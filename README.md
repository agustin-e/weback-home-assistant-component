# WeBack Robot Vacuum integration for Home Assistant
Custom component to control/automate Weback robot vacuum cleaners.

It has been tested only with the ABIR XS-X6 robot. But should work with many (most) weback controlled robot vaccuum cleaners. Please, let me know if your device is supported. This Home Assistant custom component was quite hard to create because of the complex reverse engineering process that took me several weeks of work. 

Hope you enjoy it and please, consider [buying me a cold beer 🍺](https://www.paypal.com/donate/?hosted_button_id=QQJ35P6U697H8). 

## Installation
First of all, install the component in your Home Assistant by copying the **weback_robot_vacuum** directory inside your Home Assistant's config/custom_components/ directory.

## Configuration
Add the following to your Home Assistant configuration.yaml file:

``` YAML
weback_robot_vacuum:
  username: <your WeBack email>
  password: <your WeBack password>
  region: <your country phone code> (e.g. for Argentina the code is 54).
```

Restart Home Assistant and you should see your vacuum robots available as new entities. From there you can simply add the vacuum to your dashboard in order to start/stop/return home/clean spot/ etc. etc. or create your own new automations. 
