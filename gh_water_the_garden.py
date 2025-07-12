import requests
# import schedule
import time
from time import sleep
import asyncio
from datetime import datetime
from datetime import timedelta

from kasa import Discover
from kasa import Module

import smtplib
from email.message import EmailMessage

import json 

try: 
    with open(r"..\venv\Lib\environment_parameters.json") as file:
        print('Loading environment variables from file') 
        environment_parameters = json.load(file)

        # print(environment_parameters)
        #Open Weather API Key
        API_KEY = environment_parameters.get('API_KEY')
        EMAIL_UPDATES = environment_parameters.get('email_updates')
        #Location Info
        CITY_NAME = environment_parameters.get('city_name')
        STATE_CODE = environment_parameters.get('state_code')
        ZIP = environment_parameters.get('ZIP')
        COUNTRY_CODE = environment_parameters.get('country_code', 'USA') 
        
        #email send and receive credentials
        email_address = environment_parameters.get('email_address')
        email_password = environment_parameters.get('email_password')
        email_update_to_address = environment_parameters.get('email_update_to_address')
        email_update_from_address = environment_parameters.get('email_update_from_address')

        #Smart Device Credentials
        smart_dev_username = environment_parameters.get('smart_dev_username')
        smart_dev_password = environment_parameters.get('smart_dev_password')
        smart_dev_ip = environment_parameters.get('smart_dev_ip')

        #Irrigation Parameters
        IRRIGATE_ON_STARTUP = environment_parameters.get('irrigate_on_startup',False) 
        IRRIGATE_ON_STARTUP_TIME = environment_parameters.get('irrigate_on_startup_time', 60) #in seconds
        THRESHOLD_PERCENT_CHANCE_OF_PRECIP = environment_parameters.get('percent_chance_of_precip_threshold', 0.6)
        print("Successfully loaded environment parameters")

except Exception as e:
    print(f"Error loading environment parameters: {e}")
    print(f"If no configuration file exists, this program must close") 
    exit(1) 

dry_hours = 0

def send_update_email(status, message ):
        if EMAIL_UPDATES:
            try: 
                status = status 
                time = datetime.now()

                message_to_send = f"""
Time: {time} 
Status set to: {status}
Custom Message: 
{message}
                """

                msg = EmailMessage()
                msg["Subject"] = f"IrrigationUpdate-{status}" 
                msg.set_content(message_to_send)
                msg["From"] = f"{email_update_from_address}"
                msg["To"] = f"{email_update_to_address}"

                with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.login(f"{email_address}", f"{email_password}")
                    smtp.send_message(msg) 
            except Exception as e:
                print(f"Error sending email: {e}")
                return 

def get_lat_lon(city_name, state_code, country_code='USA'):
    try:
        zip_encode_url = f'http://api.openweathermap.org/geo/1.0/direct?q={city_name},{state_code},{country_code}&limit={3}&appid={API_KEY}'
        zip_resp = requests.get(zip_encode_url)
        zip_data = zip_resp.json() 
        
        zip_lat = zip_data[0]['lat']
        zip_lon = zip_data[0]['lon']

        return zip_lat, zip_lon 
    
    except Exception as e:
        print(f"Error checking weather: {e}")
        return False
    
def get_rain_status():
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?zip={ZIP},us&appid={API_KEY}&units=imperial"
        response = requests.get(url)
        data = response.json()
        rain = data.get("rain", {})
        if "1h" in rain and rain["1h"] > 0:
            print(f"{datetime.now()}: Rain detected ({rain['1h']} mm).")
            return True
        print(f"{datetime.now()}: No rain detected.")
        return False
    except Exception as e:
        print(f"Error checking weather: {e}")
        return False
    
def get_watering_score(zip_lat, zip_lon):
    try: 
        future_url = f'http://api.openweathermap.org/data/2.5/forecast?lat={zip_lat}&lon={zip_lon}&appid={API_KEY}'
        future_resp = requests.get(future_url) 
        future_data  = future_resp.json()
        future_resp 

        codes_thunderstorm = [i for i in range(200,300)]
        codes_drizzle = [i for i in range(300,400)]
        codes_rain = [i for i in range(500,600)]

        thunderstorm_recs = 0
        drizzle_recs = 0
        rain_recs = 0 
        rain_events = []

        watering_score = 0

        forecast_focus  = [datum for datum in  future_data['list']  \
                        if int( (datetime.fromtimestamp(datum['dt']) -datetime.now() ).total_seconds()/3600 ) <= 12 \
                        ]        
        
        for item in forecast_focus:
            # check_time = datetime.fromtimestamp(datum['dt'])-timedelta(hours=9)   #wi
            delta =  datetime.fromtimestamp(item['dt']) -datetime.now()
            minutes_until_forecast = int(delta.total_seconds() )/60
            hours_until_forecast = minutes_until_forecast / 60          
            
            print(f"Forecast in {hours_until_forecast} hours -  {item['weather'][0]['main']} ({item['weather'][0]['description']})") 
            print(f"Percent of Precipitation: {item.get('pop')*100}%")
            print('------------------------------') 
            
            #Only count records OVER 60% chance of rain
            if item.get('pop', 0) > THRESHOLD_PERCENT_CHANCE_OF_PRECIP: 
                if item['weather'][0]['id'] in codes_thunderstorm:
                    thunderstorm_recs += 1
                    rain_events.append(hours_until_forecast)
                elif item['weather'][0]['id'] in codes_drizzle:
                    drizzle_recs +=1
                    rain_events.append(hours_until_forecast)
                elif item['weather'][0]['id'] in codes_rain:
                    rain_recs +=1
                    rain_events.append(hours_until_forecast)
        print(f"Rain Events ={rain_events}")
            
        if len(rain_events) == 0: 
            next_rain = 12
        else: 
            next_rain = min(rain_events) 

        if next_rain >9:
            watering_score += 3
            print(f"Next Rain: {next_rain} | adding 3 to water score")
        elif next_rain >6:
            watering_score +=2
            print(f"Next Rain: {next_rain} | adding 2 to water score")
        elif next_rain >3:
            watering_score +=1
            print(f"Next Rain: {next_rain} | adding 1 to water score")
        else:
            watering_score +=0
            print(f"Next Rain: {next_rain} | adding 0 to water score")

        if thunderstorm_recs >=1 and next_rain <=5:
            watering_score -=2
            print(f"Thunderstorms = {thunderstorm_recs} & Next Rain: {next_rain} | removing 2 from water score")
        if drizzle_recs >2 and next_rain<=3:
            watering_score -=1
            print(f"Drizzles = {drizzle_recs} & Next Rain: {next_rain} | removing 1 from water score")
        if rain_recs >1 and next_rain <=3:
            watering_score -=1 
            print(f"Rains = {rain_recs} & Next Rain: {next_rain} | removing 1 from water score")

        return watering_score
        
    except Exception as e:
        print(f"Error getting watering score: {e}")
        return False 


async def irrigate(on_off):
    try: 
        dev = await Discover.discover_single(smart_dev_ip, username=smart_dev_username, password=smart_dev_password) 
        
        # if for some reason the device is on and we are sending an on command, 
        # we want to turn it off since it SHOULD NOT be on 
        if dev.is_off and on_off == 'on':
            print('Opening Valve, triggering pump')
            await dev.turn_on() 
            await dev.update() 
            print("Pump should be on") 
            return True 
        else:
            print('Shutting down pump, closing valve')
            await dev.turn_off()
            await dev.update()
            print("Pump should be off")
            return True
        
    except Exception as e:
        print(f"Irrigation process exception: {e}")
        print(f"Error is : {e}")
        send_update_email("Irrigation Error:",f"{e}")
        return False

async def irrigate_status():
    #This will return TRUE if it is on, False if it is off, and nothing in error
    try: 
        dev = await Discover.discover_single(smart_dev_ip, username=smart_dev_username, password=smart_dev_password) 
        
        if dev.is_on == True:
            return 'On' 
        else: 
            return 'Off' 
    except Exception as e:
        print(f"Irrigation Status Exception: {e}")
        send_update_email("Irrigation Status Error:",f"{e}")
        return 'Error'


async def main():
    
    try: 
        with open("LastIrrigation.txt", "r") as li:
            text = li.read()
            if len(text) >0:
                print(f"Last irrigation found from file: {text}")
                last_date = datetime.fromisoformat(text) 
                last_irrigation_on = last_date
            else:
                print('No Irrigation Record found; using now() ')
                last_irrigation_on = datetime.now() 
    except:
        print("file read error. Using default of now() ")
        last_irrigation_on = datetime.now() 

    send_update_email("starting","Just starting Irrigation Protocol")
    
    # Session variables to initialize
    pm_hours = [22, 23, 0, 1, 2, 3, 4, 5]

    watering_time = 0
    run_through = 0
    status_text = ''
    
    last_irrigation_off = last_irrigation_on
    last_rain_event = datetime.fromtimestamp(1294790400)    
    irrigation_outcome = 'Just starting!'
    irrigation_error = False 

    #If we irrigate on startup, use the parameters for irrigation timing
    # Make sure to catch if the irrigation does not turn off
    # TODO: However, the 'while' loop here could probably be eliminated since we check if its on 
    # when not supposed to be below as part of startup
    if IRRIGATE_ON_STARTUP:
        await irrigate('on') 
        sleep(IRRIGATE_ON_STARTUP_TIME) # for irrigation on startup, only water for 60 seconds 
        irrigation_outcome = await irrigate('off') 
        while not irrigation_outcome:
            print("Irrigation did not turn off. Retrying")
            irrigation_outcome = await irrigate('off')
            time.sleep(10)

    
    print("Starting garden irrigation watcher...")
    lat, lon = get_lat_lon(CITY_NAME,STATE_CODE, COUNTRY_CODE) 
    
    with open("watering_log.txt", "a") as f:
        f.writelines(f"{datetime.now()} - Program Initiated | watching for coordinates- {lat},{lon}\n")

    #I feel like this step should not be necessary, but prior attempt to just use T/F return status did not work 
    status_text = await irrigate_status()

    if status_text == 'On':
        print("ERROR: IRRIGATION SHOULD BE OFF BUT REPORTS ON!")
        send_update_email("ERROR","IRRIGATION SHOULD BE OFF BUT REPORTS ON!")

        with open("watering_log.txt", "a") as f:
            f.writelines(f"{datetime.now()} - ERROR: IRRIGATION SHOULD BE OFF BUT REPORTS ON!\n")
        #the system reports ON but should be OFF; turn it off now!
        on_off = 'off'
        await irrigate(on_off)
        last_irrigation_off = datetime.now() 

    
    mins_since_irrigation_on = (datetime.now()- last_irrigation_on).seconds/60
    mins_since_irrigation_off = (datetime.now()- last_irrigation_off).seconds/60

    print(f"Run Through: {run_through}")
    print(f"Mins since last irrigation: {mins_since_irrigation_on}")

    while True: 
        print(f"minutes since last irrigation: {mins_since_irrigation_on} - In Loop")
        send_update_email("Checking",f"Run Through = {run_through} |Status = {status_text}")   
        if get_rain_status():
            time.sleep(300) # If it says rain, wait and check again to be sure
            if get_rain_status():
                print('rain reported') 
                send_update_email("Rain Reported",f"Run Through = {run_through}")
                last_rain_event = datetime.now()    
                with open("watering_log.txt", "a") as f:
                    f.writelines(f"{datetime.now()} - Rain Reported | Not Irrigating\n")
                
                irrigation_outcome = 'Rain reported, so not going to worry'
            else: 
                print("Saw rain first, waited and now not seeing rain. could be an error")
                irrigation_outcome = 'Saw rain, and on re-check, found none. Moving on'

        else: 
            water_score = get_watering_score(lat, lon)
            print(f"Water Score is {water_score}")
            with open("watering_log.txt", "a") as f:
                    f.writelines(f"{datetime.now()} - Watering Score Reported: {water_score}\n")

            mins_since_rain_event = (datetime.now() - last_rain_event)
            if mins_since_rain_event.days >0:
                mins_since_rain_event = 999
            else: 
                mins_since_rain_event = mins_since_rain_event.seconds / 60
            print(f"Last rain: {last_rain_event}")
            print(f"Minutes since last logged Rain Event: {mins_since_rain_event}")

            if water_score>=1 and mins_since_irrigation_on >=90 and mins_since_rain_event >=60:
                print(f"Water Score is {water_score} | Fire the sprinklers")
                               
                watering_time = 90 #1.5 minutes by default
                watering_time += 30*water_score # Add based on water score
                if datetime.now().hour in pm_hours:
                    print("Its night time; watering half as much")
                    watering_time = watering_time / 2
                    
                with open("watering_log.txt", "a") as f:
                    f.writelines(f"{datetime.now()} - Irrigation turning on for {watering_time} seconds\n")
                    print(f"{datetime.now()} - Irrigation turning on for {watering_time} seconds aka {watering_time/60} mins\n")
                
                outcome = await irrigate('on') 
                if not outcome:  #Program did not hit an error
                    last_irrigation_on = datetime.now()               
                    send_update_email("Activating",f"Activating Irrigation for {watering_time/60} mins. Run Through = {run_through}, Water Score = {water_score}")
                    time.sleep(watering_time) # This is the watering time
                    outcome = await irrigate('off')
                    
                    looper = 0
                    while not outcome:
                        looper += 1
                        print(f"Irrigation did not turn off. Retrying. Attempt: {looper}")
                        outcome = await irrigate('off')
                        time.sleep(10) # wait 10 seconds before trying again
                        print("If this doesn't shut off, its a problem") 
                    print("Irrigation turned off successfully")
                    last_irrigation_off = datetime.now() 
                    send_update_email("Deactivating",f"Deactivating Irrigation. Run time should have been {watering_time/60} mins. Run Through = {run_through}, Water Score = {water_score}")
                
                    with open("watering_log.txt", "a") as f:
                        f.writelines(f"{datetime.now()} - Irrigation turned off\n")
                        print("Plug Off:")

                    irrigation_outcome = 'Received a call for water. Went through with irrigation.'
                else:
                    print("Irrigation did not turn on properly. It hit an exception") 
                    irrigation_error = True 

            elif mins_since_irrigation_on <90: 
                print(f"We watered {mins_since_irrigation_on} minutes ago. Ignoring any call for water")
                irrigation_outcome = 'We irrigated recently, so no need to do it now'
                
        status_text = await irrigate_status()       
        send_update_email("Waiting",f"Irrigation Status = {status_text}. Run time would have been {watering_time/60} mins. Run Through = {run_through}, Water Score = {water_score}. Irrigation Notes: {irrigation_outcome}")
        
        await irrigate('off') #Extra try to make sure the irrigation turns off before sleeping
        
        try: 
            with open("LastIrrigation.txt", "w") as li:
                li.write(f"{last_irrigation_off}")
        except:
            print("file write error. Local Variable only ")
            last_irrigation_off = datetime.now() 
        
        #If it was unable to water, run the program after 60 seconds by only waiting 60 seconds
        if irrigation_error:
            wait_time = 60
            irrigation_error = False #set to false so that we don't get stuck in this statement
        #Else wait a different amount of time (30-60 minutes))
        else: 
            wait_time = 3600 / 2 
        
        
        with open("watering_log.txt", "a") as f:
                    f.writelines(f"{datetime.now()} - Irrigation Routine Over | Waiting {wait_time}\n")
        print(f"Last On event: {last_irrigation_on} | Last Off Event: {last_irrigation_off} | Last Rain Event: {last_rain_event}")
        print(f"{datetime.now()} - Sleeping for {wait_time/60} minutes")
         
        time.sleep(wait_time)
       
        mins_since_irrigation_on = (datetime.now()- last_irrigation_on).seconds/60
        run_through+=1
        print(f"""
              ----  Here we go again!------------
              -- Starting Round {run_through} --
""")
        

if __name__ == "__main__":
    asyncio.run(main())