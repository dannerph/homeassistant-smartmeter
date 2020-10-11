# Smartmeter [[Home Assistant](https://www.home-assistant.io/) Component]

custom component for home assistant to read IEC62056-21 meter values from e.g. IR-USB connection

## Basic Installation/Configuration Instructions

Copy content of custom_components to your local custom_components folder and add the following lines to your configuration.

### Configuration:

```yaml
smartmeter:
  port: /dev/ttyUSB0
  obis:
    - 1-0:1.8.0*255
    - 1-0:2.8.0*255
```

Explanation:

* **port**: The tty port your reading head is connected to.
* **obis**: a list of obis numbers to add sensors for (check debug logs to see which values are extracted from the readings).
