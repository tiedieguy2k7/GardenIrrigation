# GardenIrrigation
This will check Open Weather's API for current and upcoming rain events, and trigger a smart device which is used to water your garden
This code uses the Kasa smart device library to do simple on/off and status checks

The initial algorithm was basically "Is it raining, or will it rain in 3 hours? No = Run Garden irrigation for 3 minutes. Yes = Do nothing and wait"
The algorithm has now improved a bit more to account for different rain scenarios and creates a 'water score'. Using this water score we adjust how much to water the garden (time wise)
Future developments will take into account Sun vs. Clouds (evaporation is an issue), % chance of future precipitions, and temperature.

Credentials should be stored in an Environment path or other secure location


Hardware Used:
Normally Closed Solenoid Valve (if no power, no water). This isn't the exact one I got, but I can't find my order
https://ussolid.com/products/u-s-solid-electric-solenoid-valve-3-4-110v-ac-solenoid-valve-brass-body-normally-closed-viton-seal-html?country=US&gad_source=1&gad_campaignid=1332194851&gbraid=0AAAAAD2ek2oSPZVUG2NvoXedQyYbnls8b&gclid=Cj0KCQjwjo7DBhCrARIsACWauSke5NsqS3h39kGRtrhkZcaljH46h5TMU3MlXFE8FJv6dF93eDmbccIaAmsKEALw_wcB

Bulkhead Fitting (to thread pipe to the bottom of the barrel):
https://www.amazon.com/dp/B0CSN53G5J?ref=ppx_yo2ov_dt_b_fed_asin_title

Smart Plug: (This is an older plug, and Kasa makes newer ones. Check the python library for supported models)
https://www.amazon.com/dp/B0178IC734?ref_=ppx_hzsearch_conn_dt_b_fed_asin_title_5 

Various fittings to connect from valve to Pex. 
1/2" Pex TUbing 
1/2" Pex Crimp Rings
1/2" Pex Elbows and Tees 

Irrigation Kit: 
https://www.amazon.com/dp/B0BX4ZZCX4?ref_=ppx_hzsearch_conn_dt_b_fed_asin_title_1&th=1
