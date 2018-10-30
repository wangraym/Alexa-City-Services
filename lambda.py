import boto3
import datetime
import os
from botocore.vendored import requests
from boto3.dynamodb.conditions import Key, Attr

global QUERY
global STATUS
global USERID
global SESSIONID

#---------------- Example Dynamo DB Entry --------------------------------------


data = {
  "City": "toronto",
  "items": [
    {
      "Hours": {
        "0": "7:00-15:00",
        "1": "7:00-15:00",
        "2": "7:00-15:00",
        "3": "7:00-15:00",
        "4": "7:00-15:00",
        "5": "7:00-15:00",
        "6": "7:00-15:00"
      },
      "Name": "Limited",
      "Arn": "SNS ARN Here"
    },
    {
      "Hours": {
        "all": "all"
      },
      "Name": "Abrams",
      "Arn": "SNS ARN"
    },
    {
      "Hours": {
        "all": "all"
      },
      "Name": "V. I. P. Towing",
      "Arn": "SNS ARN"
    }
  ],
  "Service": "towing"
}

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session, card_type="Simple"):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': card_type,
            'title': "SessionSpeechlet - " + title,
            'content': "SessionSpeechlet - " + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }

def build_permission_card(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        "card": {
          "type": "AskForPermissionsConsent",
          "permissions": [
            "alexa::profile:mobile_number:read",
            "alexa::profile:name:read"
          ]
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }

def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }
    


# --------------- Functions that handle skill intents -------------------------

def menu(speech_output=""):
    # Main Menu
    
    global QUESTION
    QUESTION = 'city'
    
    speech_output += "Welcome to Services. When you are ready, "
    return ask(speech_output=speech_output)
    
def return_to_menu(intent, session):
    # Confirm Return to Main Menu
    
    global QUERY
    global QUESTION
    
    # Once the user provides confirmation
    if intent['name'] == 'answer':
        if 'value' in intent['slots']['yesno']:
            if intent['slots']['yesno']['value'] == 'yes':
                return menu(speech_output="Okay. Returning you to the main menu. ")
            else:
                return ask(intent, session)
        
        session_attributes = {'query': QUERY, 'status': 'returnMenu', question: QUESTION}
        card_title = "return"
        speech_output = "Invalid answer. Are you sure you want to start over?"
        reprompt_text = "I didn't understand that, please try again. Say menu if you would like to hear the options again."
        should_end_session = False
        return build_response(session_attributes, build_speechlet_response(
            card_title, speech_output, reprompt_text, should_end_session))
    
    session_attributes = {'query': QUERY, 'status': 'returnMenu', 'question': QUESTION}
    card_title = "return"
    speech_output = "Are you sure you want to start over?"
    reprompt_text = "I didn't understand that, please try again. Say menu if you would like to hear the options again."
    should_end_session = False
    
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))
        

def answer(intent, session):
    # Route the user response to the appropriate function based on status
    
    global STATUS
    
    if STATUS == 'query': # Additional Query Parameters required
        return query(intent, session)
    elif STATUS == 'search': # Grab query results
        return search(intent, session)
    elif STATUS == 'send': # Notify services
        return send(intent, session)
    elif STATUS == 'returnMenu': # Start over
        return return_to_menu(intent, session)
    else:
        pass

def query(intent, session):
    # Validate answer and ask for the next query parameter
    
    global QUERY
    global STATUS
    global QUESTION
    
    # Check for valid answer
    if 'value' not in intent['slots']['generic']:
        return ask(intent, session, True)
  
    answer = intent['slots']['generic']['value'].lower()
    
    if QUESTION == 'city':
        
        QUERY['city'] = answer
        QUESTION = 'service'
        
        return ask(intent, session)
        
    elif QUESTION == 'service':
        
        QUERY['service'] = answer
        return search(intent, session)

def ask(intent="", session="", invalid=False, speech_output=""):
    # Generate response text for next question. I use this to route what to say from all 
    
    global QUESTION
    global QUERY
    
    if invalid == True:
        speech_output += "Invalid answer. "
      
    if QUESTION == 'city':
        session_attributes = {'query': {}, 'status': 'query', 'question': 'city'}
        card_title = "Welcome"
        speech_output += "say search, followed by the name of a registered city."
        reprompt_text = "I didn't understand that, please try again. Say menu if you would like to hear the options again."
        should_end_session = False
        return build_response(session_attributes, build_speechlet_response(
            card_title, speech_output, reprompt_text, should_end_session))

    elif QUESTION == 'service':
        session_attributes = {'query': QUERY, 'status': 'query', 'question': 'service'}
        card_title = "query"
        speech_output = "Say search followed by the service you are looking for"
        reprompt_text = speech_output
        should_end_session = False
    
        return build_response(session_attributes, build_speechlet_response(
            card_title, speech_output, reprompt_text, should_end_session))
    
    elif QUESTION == 'done':
        return search(intent, session, "Invalid answer. ")

def search(intent, session, speech_output=""):
    # Take answers and Query for results
    
    global QUERY
    global STATUS
    
    QUERY['time'] = datetime.datetime.now()
    
    response = get_results(QUERY)
    
    QUERY['time'] = str(QUERY['time'])
    
    if len(response) == 0:
  
        speech_output += "Sorry, there are no " + QUERY['service'] + "services available in " + QUERY['city'] + "at this time. Returning you to the main menu. "
    
        return menu(speech_output)
        
    elif len(response) == 1:
        
        session_attributes = {'query': QUERY, 'status': 'send', 'response': response, 'question': 'done'}
        card_title = "Ask to send"
        speech_output += "I found one available " + QUERY['service'] + " service in " + QUERY['city'] + " called " + response[0]['Name'] + ". Would you like to request this service? Your phone number will be provided to them to contact you as soon as possible."
        should_end_session = False
        reprompt_text = speech_output
        return build_response(session_attributes, build_speechlet_response(
            card_title, speech_output, reprompt_text, should_end_session))
            
    else:
      
        session_attributes = {'query': QUERY, 'status': 'send', 'response': response, 'question': 'done'}
        card_title = "Ask to send"
        speech_output += "I found " + str(len(response)) + " services. Say the corresponding number of the service to request that service, or say all, to contact all of them. "
        
        for i in range(len(response)):
          speech_output += "Service " + str(i+1) + ": " + response[i]['Name'] + ". "
        
        should_end_session = False
        reprompt_text = speech_output
        return build_response(session_attributes, build_speechlet_response(
            card_title, speech_output, reprompt_text, should_end_session))  
    

def get_results(query):
    # Search table, return results
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['TableName'])
    
    response = table.query(
        KeyConditionExpression=Key('City').eq(query['city']) & Key('Service').eq(query['service'])
    )

    r = []
    
    if response['Count'] == 1:
        
        for result in response['Items'][0]['items']:
            
            if 'all' in result['Hours']:
                r.append(result)
            
            else:
                hours = result['Hours'][str(query['time'].weekday())]
                hours = hours.split('-')
                hours[0] = hours[0].split(':')
                hours[1] = hours[1].split(':')
                
                if query['time'].time() > datetime.time(int(hours[0][0]), int(hours[0][1])):
                    if query['time'].time() < datetime.time(int(hours[0][0]), int(hours[0][1])):
                        r.append(result)
            
    return r

def send(intent, session):
    # Notify selected service(s)
    
    global QUERY
    global STATUS
    global QUESTION
    global RESPONSE
    
    # Check if permissions have been granted first
    perms = ['Name', 'Phone Number']
    contact = {}
    
    for i in perms:
        status_code, r = get_api(i)

        if status_code != 0:
            if status_code == 204:
                
                return handle_session_end_request("A " + i + " has not been linked to this account. ")
                
            elif status_code == 403:
                session_attributes = {'query': QUERY, 'status': STATUS, 'question': QUESTION, 'response': RESPONSE}
                card_title = "Welcome"
                speech_output = "Permission to access your contact information has not been granted. Please view the Alexa app to allow permissions, and speak your answer again" 
                reprompt_text = "I didn't understand that, please try again. Say menu if you would like to hear the options again."
                should_end_session = False
                
                return build_response(session_attributes, build_permission_card(
                    card_title, speech_output, reprompt_text, should_end_session))
        
        contact[i] = r    
    
    # Check for valid answer
    
    if len(RESPONSE) == 1:
        if 'value' not in intent['slots']['yesno']:
            return ask(intent, session, True)
        else:
            answer = 0
    
    else:
        if 'value' not in intent['slots']['number']:
            if 'value' not in intent['slots']['sendall']:
                return ask(intent, session, True)
            else:
                answer = 0
        else:
            answer = int(intent['slots']['number']['value']) - 1
            if answer < 1 or answer > len(RESPONSE):
                return ask(intent, session, True)
    
    sns = boto3.client('sns')
    
    if answer == 0:
        
        for i in range(len(RESPONSE)):
            print(RESPONSE)
            sns.publish(
                TopicArn=RESPONSE[i]['Arn'],
                Message='Hello ' + RESPONSE[i]['Name'] + ' from city services. A user named ' + contact['Name'] + ' has requested your ' + QUERY['service'] + 
                ' service. Please contact them at phone: ' + contact['Phone Number']['countryCode'] + ' ' + contact['Phone Number']['phoneNumber'],
                Subject='Service Request'
            )
        
    
    else:
        
        sns.publish(
            TopicArn=RESPONSE[answer]['Arn'],
            Message='Hello ' + RESPONSE[answer]['Name'] + ' from City Services. A user named ' + contact['Name'] + ' has requested your ' + QUERY['service'] + 
            ' service. Please contact them at phone: ' + contact['Phone Number']['countryCode'] + ' ' + contact['Phone Number']['phoneNumber'],
            Subject='Service Request'
        )

    return menu(speech_output="Request sent. Returning to the main menu. ")

def get_api(key):
    # Check/GET user info
    
    global APITOKEN
    global APIENDPOINT  
    
    end = {"Name": "/v2/accounts/~current/settings/Profile.name", "Phone Number": "/v2/accounts/~current/settings/Profile.mobileNumber"}
    
    token = "Bearer " + APITOKEN
    url = APIENDPOINT + end[key]
    headers={'authorization': token, "Accept":"application/json"}
    
    r = requests.get(url, headers=headers)
    
    if r.status_code == 200:
        return (0, r.json())
    
    else:
        return (r.status_code, "")
        
        
def handle_session_end_request(speech_output=""):
    # End session response
    
    card_title = "Session Ended"
    speech_output += "Thank you for using Services"
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))

# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """
    
    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
          
    session_attributes = {'query': {}, 'status': 'query', 'question': 'city'}
    card_title = "Welcome"
    speech_output = "Welcome to Services. On the Alexa app, please grant permission to access your Amazon account contact information. It will be provided to any services you choose to request using this skill. When you are ready, say search, followed by the name of a registered city."
    reprompt_text = "I didn't understand that, please try again. Say menu if you would like to hear the options again."
    should_end_session = False
    
    
    return build_response(session_attributes, build_permission_card(
        card_title, speech_output, reprompt_text, should_end_session))


def on_intent(intent_request, session):

    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']
    
    global QUERY 
    QUERY = session['attributes']['query']
    global STATUS 
    STATUS = session['attributes']['status']
    global QUESTION
    QUESTION = session['attributes']['question']
    
    if 'response' in session['attributes']:
        global RESPONSE
        RESPONSE = session['attributes']['response']
    
    if intent_name == "answer":
        return answer(intent, session)
    elif intent_name == "menu":
        return return_to_menu(intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        return route_help(intent, session)
    elif intent_name == "AMAZON.FallbackIntent":
        return route_help(intent, session)
    else:
        return handle_session_end_request()

def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
          


# --------------- Main handler ------------------

def lambda_handler(event, context):

    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    global USERID
    USERID = event['session']['user']['userId']
    global SESSIONID
    SESSIONID = event['session']['sessionId']
    global APITOKEN
    APITOKEN = event['context']['System']['apiAccessToken']
    global APIENDPOINT
    APIENDPOINT = event['context']['System']['apiEndpoint']
    
    if (event['session']['application']['applicationId'] != os.environ['skillArn']):
        raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])
