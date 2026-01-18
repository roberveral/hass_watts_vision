# Watts Vision Integration for Home Assistant

A Home Assistant custom integration for Watts Vision smart heating systems, enabling comprehensive control of your thermostat devices directly from Home Assistant.

## Overview

[Watts Vision](https://www.wattselectronics.com/) is a smart heating management system designed for precise room temperature control. This integration uses the Watts Vision cloud API to provide real-time monitoring and control of your heating zones, including temperature adjustments, mode changes, and energy consumption tracking.

## Features

- **Climate Control**: Full thermostat control with HVAC modes (Heat, Cool, Off) and preset modes (Comfort, Eco, Program, Boost, Anti-Freeze)
- **Multiple Temperature Settings**: Configure different temperature settings for various modes (Comfort, Eco, Boost, Anti-Freeze, Manual)
- **Real-time Monitoring**: Track current temperature, target temperature, and HVAC action (heating, cooling, idle)
- **Multiple Entities per Device**:
  - Climate entity for thermostat control
  - Temperature sensor for current room temperature
  - HVAC setting sensor (Heat/Cool mode)
  - Battery sensor for low battery detection
- **Central Unit Monitoring**: 
  - System-wide HVAC setting sensor
  - Communication delay sensor to monitor connectivity
- **Custom Services**: Advanced service to set multiple temperature settings at once
- **Optimistic Updates**: Instant UI feedback when changing settings

## Installation

### Option 1: Manual Installation

1. Download or clone this repository
2. Copy the `custom_components/watts_vision` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant
4. Go to **Settings** > **Devices & Services**
5. Click **+ Add Integration**
6. Search for "Watts Vision" and follow the configuration steps

### Option 2: HACS (Home Assistant Community Store)

**Note**: This integration is not yet available in the default HACS repository. To install via HACS:

1. Open HACS in your Home Assistant instance
2. Click on the three dots in the top right corner
3. Select **Custom repositories**
4. Add this repository URL: `https://github.com/roberveral/hass_watts_vision` (replace with actual repository URL)
5. Select **Integration** as the category
6. Click **Add**
7. Find "Watts Vision" in HACS and click **Download**
8. Restart Home Assistant
9. Go to **Settings** > **Devices & Services** > **+ Add Integration** > **Watts Vision**

## Configuration

### Prerequisites

Before setting up the integration, ensure you have:

1. A Watts Vision account (created via the Watts Vision mobile app)
2. At least one Watts Vision gateway connected to the internet
3. One or more thermostat devices paired with your gateway
4. Your Watts Vision account credentials (username and password)

### Setup Steps

1. Navigate to **Settings** > **Devices & Services** in Home Assistant
2. Click **+ Add Integration**
3. Search for "Watts Vision"
4. Enter your Watts Vision account credentials:
   - **Username**: Your Watts Vision account email
   - **Password**: Your Watts Vision account password
5. Select the Smart Home (gateway) you want to integrate
6. Click **Submit**

The integration will automatically discover all thermostats associated with the selected Smart Home and create the corresponding entities.

### Configuration Options

After setup, you can configure additional options:

1. Go to **Settings** > **Devices & Services**
2. Find the Watts Vision integration
3. Click **Configure**

Available options:
- **Scan Interval**: How often to poll the Watts Vision API for updates (default: 15 seconds)
- **Boost Duration**: Duration for Boost mode when activated (default: 2 hours)

## Usage Guide

### Climate Entities

Each thermostat device is represented as a climate entity with the following capabilities:

#### HVAC Modes

- **Heat**: Manual heating mode (Comfort or Eco)
- **Cool**: Manual cooling mode (Comfort or Eco)
- **Off**: Turn off heating/cooling for the zone

#### Preset Modes

- **Comfort**: Maintain the configured comfort temperature
- **Eco**: Maintain the energy-saving eco temperature
- **Program**: Follow the programmed schedule
- **Boost**: Temporary high-temperature boost for the configured duration
- **Anti-Freeze**: Maintain minimum temperature to prevent freezing

#### Setting Temperature

You can adjust the target temperature of the thermostat.

### Temperature Sensors

Each thermostat exposes a temperature sensor entity that reports the current ambient temperature. This sensor can be used independently in automations, scripts, or dashboards.

### HVAC Setting Sensors

Each thermostat includes an HVAC setting sensor that indicates whether the system is in Heat or Cool mode:
- **Per-Device Sensor** (diagnostic)
- **Central Unit Sensor** (diagnostic)

### Battery Sensors

Each battery-powered thermostat includes a battery sensor that indicates if the battery is low.

### Communication Delay Sensor

The central unit exposes a communication delay sensor that reports the time since the last successful communication with Watts servers. High values may indicate connectivity issues.

## Custom Services

### Set Temperature Settings

The `watts_vision.set_temperature_setting` service allows you to configure multiple temperature settings without changing the current mode.

**Service**: `watts_vision.set_temperature_setting`

**Target**: Climate entities

**Parameters**:
- `temperature_comfort` (optional): Set the comfort temperature
- `temperature_eco` (optional): Set the eco temperature
- `temperature_boost` (optional): Set the boost temperature
- `temperature_antifreeze` (optional): Set the anti-freeze temperature
- `temperature_manual` (optional): Set the manual temperature

**Example**:
```yaml
service: watts_vision.set_temperature_setting
target:
  entity_id: climate.living_room
data:
  temperature_comfort: 21.5
  temperature_eco: 18.0
  temperature_boost: 24.0
```

This is useful for seasonal adjustments or automations based on weather conditions.

## Troubleshooting

### Devices Appear as Unavailable

**Symptom**: Climate entities show as "Unavailable"

**Cause**: Communication issue between the gateway and Watts Vision cloud service

**Resolution**:
1. Check the gateway status in the Watts Vision mobile app
2. Verify the gateway shows as online
3. Check WiFi connection strength
4. Restart the gateway by unplugging it for 10 seconds
5. Reload the integration in Home Assistant:
   - Go to **Settings** > **Devices & Services**
   - Find Watts Vision integration
   - Click the three-dot menu and select **Reload**

### Newly Added Devices Not Appearing

**Symptom**: Devices added in the Watts Vision app don't appear in Home Assistant

**Cause**: Integration caches device list for performance

**Resolution**:
Wait up to 15 minutes for automatic device discovery, or reload the integration immediately:
1. Go to **Settings** > **Devices & Services**
2. Find Watts Vision integration
3. Click the three-dot menu and select **Reload**

### Commands Not Taking Effect

**Symptom**: Temperature or mode changes don't seem to work

**Cause**: Possible connectivity delay or API issues

**Resolution**:
1. Check the communication delay entity for high values
2. Verify Central Unit connectivity in the Watts Vision mobile app
3. Check Home Assistant logs for error messages
4. Wait 20-30 seconds for the API to process the command, and try again
5. If issues persist, restart the Central Unit

### Authentication Failed

**Symptom**: "Invalid authentication" error during setup

**Resolution**:
1. Verify your username and password are correct
2. Ensure you can log in to the Watts Vision mobile app with the same credentials
3. Check for any special characters in your password that may need escaping
4. If you recently changed your password, use the new credentials

## Data Updates

The integration polls data from the Watts Vision cloud API every 15 seconds by default. After sending commands (temperature changes, mode changes), the integration waits 20 seconds before refreshing to allow the device to process the change and prevents inconsistent state updates.

## Known Limitations

- **Cloud Polling**: The integration uses cloud polling (IoT Class: cloud_polling) rather than push notifications, which may result in slight delays in state updates
- **HVAC Setting**: The system-wide HVAC setting (Heat/Cool) cannot be changed via the API and must be configured manually on the central unit or through the Watts Vision app
- **Program Schedules**: While the integration supports Program mode, the actual program schedules must be configured in the Watts Vision mobile app
- **Floor Temperature**: While floor temperature data is available from the API, only air temperature is currently exposed as the primary temperature sensor

## Contributing

Contributions are welcome! If you find bugs or have feature requests, please open an issue on the GitHub repository.

## License

This project is licensed under the [Apache 2.0 License](LICENSE.md).

## Credits

- **Author**: [@roberveral](https://github.com/roberveral)
- **Integration Version**: 0.1.0
- **Home Assistant Domain**: `watts_vision`

Inspired by the work of:

- [@pwesters](https://github.com/pwesters/watts_vision)
- [@NoWarries](https://github.com/NoWarries/watts_vision)

## Support

For issues specific to this integration:
- Check the [troubleshooting section](#troubleshooting) above
- Review Home Assistant logs for error messages
- Open an issue on GitHub with detailed information about your setup and the problem

For issues with Watts Vision devices or the mobile app:
- Contact Watts Vision support
- Consult the Watts Vision user manual

---

**Note**: This is a custom integration and is not officially affiliated with or supported by Watts Electronics.
