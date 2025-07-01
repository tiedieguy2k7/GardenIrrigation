# GardenIrrigation
This will check Open Weather's API for current and upcoming rain events, and trigger a smart device which is used to water your garden
This code uses the Kasa smart device library to do simple on/off and status checks

The initial algorithm was basically "Is it raining, or will it rain in 3 hours? No = Run Garden irrigation for 3 minutes. Yes = Do nothing and wait"
The algorithm has now improved a bit more to account for different rain scenarios and creates a 'water score'. Using this water score we adjust how much to water the garden (time wise)
Future developments will take into account Sun vs. Clouds (evaporation is an issue), % chance of future precipitions, and temperature.


