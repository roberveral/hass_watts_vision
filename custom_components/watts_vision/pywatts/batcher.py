"""Batcher for Watts Vision API device updates.

Handles debouncing and queueing device updates against the API to avoid
concurrent updates in the system that may get lost.
"""

import asyncio
import logging

from .api import WattsApiClient

DEFAULT_DEBOUNCE_DELAY: float = 2.0
DEFAULT_QUEUE_DELAY: float = 2.0

_LOGGER = logging.getLogger(__name__)


def _get_device_key(smart_home_id: str, device_id: str) -> tuple[str, str]:
    return (smart_home_id, device_id)


class WattsDeviceApiBatcher:
    """Implements debouncing and queueing logic for Watts Vision device updates.

    Watts Vision API works asynchronously for updates. When launching several updates
    concurrently, it sometimes just ignores some of them. Deboncing and queueing allows
    to limit the number of concurrent updates running on the system.
    """

    def __init__(
        self,
        client: WattsApiClient,
        debounce_delay: float = DEFAULT_DEBOUNCE_DELAY,
        queue_delay: float = DEFAULT_QUEUE_DELAY,
    ):
        """Initialzes a WattsDeviceApiBatcher."""
        self._client = client
        self._debounce_delay = debounce_delay
        self._queue_delay = queue_delay
        self._update_queue: asyncio.Queue = asyncio.Queue()
        self._pending_settings: dict[(str, str), dict] = {}
        self._debounce_tasks: dict[(str, str), asyncio.Task] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def async_update_device(
        self,
        smart_home_id: str,
        device_id: str,
        settings: dict,
    ) -> None:
        """Update device settings in the Watts Vision API.

        The settings dictionary should contain the parameters to be updated
        for the device, as they are defined in the Watts Vision API.

        It accumulates updates to the same device during the debounce window
        so a single update is emitted against the Watts Vision system. Debounce
        means that the update is only performed once there has not been updates
        to a device during a specified time window.
        """

        async with self._lock:
            device_key = _get_device_key(smart_home_id, device_id)
            # Merge new changes into the pending settings for this device
            if device_key not in self._pending_settings:
                self._pending_settings[device_key] = {}
            self._pending_settings[device_key].update(settings)

            # Reset the debounce timer if it's already running for this device
            if (
                device_key in self._debounce_tasks
                and not self._debounce_tasks[device_key].done()
            ):
                self._debounce_tasks[device_key].cancel()

            # Start a new debounce countdown for this device
            self._debounce_tasks[device_key] = asyncio.create_task(
                self._async_debounce_update(device_key)
            )

    async def _async_debounce_update(self, device_key: str) -> None:
        try:
            # Wait the debounce window before performing the update
            await asyncio.sleep(self._debounce_delay)

            async with self._lock:
                if device_key not in self._pending_settings:
                    return
                # Get final settings for the device
                settings = self._pending_settings.pop(device_key)

                _LOGGER.debug(
                    "Queuing debounced device update to %s: %s", device_key, settings
                )

                # Remove the debounce task from tracking
                self._debounce_tasks.pop(device_key, None)

            # Queue the settings update to the device
            await self._update_queue.put((device_key, settings))

        except asyncio.CancelledError:
            # Reset the debounce window when a new update arrives before the timer finishes.
            pass

    async def async_update_worker(self) -> None:
        """Worker that processes device updates against Watts Vision API sequentially.

        As the Watts Vision system performs updates asynchronously, launching updates for
        several devices in parallel may imply that some updates are lost. By doing it sequentially
        with a safe delay between devices, it improves the situation by ensuring the system
        is never overwhelmed.
        """

        while True:
            # Get next device update from the queue
            try:
                device_key, settings = await self._update_queue.get()
                smart_home_id, device_id = device_key
            except asyncio.QueueShutDown:
                _LOGGER.debug(
                    "Watts update queue is shutdown and work has finished. Gracefully finishing worker"
                )
                return

            _LOGGER.debug("Update task for Watts device %s received", device_key)

            try:
                # Perform the actual update against Watts Vision API
                await self._client.async_update_device(
                    smart_home_id, device_id, settings
                )
            finally:
                self._update_queue.task_done()
                _LOGGER.debug("Update task for Watts device %s completed", device_key)
                # Breath window for the API before processing the next device update
                await asyncio.sleep(self._queue_delay)

    async def async_worker_shutdown(self) -> None:
        """Gracefully shuts down the worker process that performs updates to the Watts Vision system.

        New updates will be rejected and the remaining ones will be performed before actually finishing.
        """
        self._update_queue.shutdown()

        if not self._update_queue.empty():
            await self._update_queue.join()

    def size(self) -> int:
        """Returns the number of updates still to make agasint the Watts Vision system."""

        return self._update_queue.qsize() + len(self._pending_settings)
