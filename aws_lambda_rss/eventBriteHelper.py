import asyncio
import json

from aiohttp import ClientSession
from datetime import datetime
from requests import Session

session = Session()
headers = {
    "Authorization": "Bearer <key>",
    "Content-Type": "application/json"
}

eventBriteApiUrl = "https://www.eventbriteapi.com/v3/"
organisationId = "464103861019"

monthNames = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
preevent = "<rss version=\"2.0\" xmlns:content=\"http://purl.org/rss/1.0/modules/content/\" xmlns:atom=\"http://www.w3.org/2005/Atom\"><channel>"
eventTemplate = ""
postevent = "</channel></rss>"


async def fetchEventTicketClasses(session, eventId):
    url = eventBriteApiUrl + "events/" + str(eventId) + "/ticket_classes/"
    async with session.get(url=url, headers=headers) as response:
        responseJson = await response.json()
        return {'eventId': eventId, 'response': responseJson}


def getOrganisationEvents(organisationId):
    eventsUrl = eventBriteApiUrl + "organizations/" + \
        str(organisationId) + "/events/"
    response = session.get(url=eventsUrl, headers=headers)
    return json.loads(response.text)['events']


async def getEventTicketClasses(eventData):
    async with ClientSession() as session:
        asyncTasks = []
        for event in eventData:
            asyncTasks.append(fetchEventTicketClasses(session, event['id']))

        responses = await asyncio.gather(*asyncTasks, return_exceptions=True)

        ticketClassData = {}
        for response in responses:
            if response['response']['pagination']['object_count'] == 0:
                continue

            ticketClassData[response['eventId']] = response['response']

        return ticketClassData


def processOrganisationEventsResponse(response):
    global organisationEvents
    organisationEvents = json.loads(response.text)


def processEventTicketClassesResponse(response):
    global ticketClasses
    ticketClasses = json.loads(response.text)['ticket_classes']


def getEventsAsHtml(event, lambda_context):
    content = ""
    dropins = ""
    huddles = ""
    workshops = ""

    widgets = ""

    eventData = getOrganisationEvents(organisationId)
    ticketClassData = asyncio.run(getEventTicketClasses(eventData))

    for event in eventData:

        if event['status'] != "live":
            continue

        eventId = event['id']

        ticketClasses = ticketClassData[eventId]['ticket_classes']
        onSaleStatus = '' if ticketClasses == [] else ticketClasses[0]['on_sale_status']

        eventClass = ''
        registerButtonClass = 'btn-primary'
        registerButtonText = 'Register'
        if onSaleStatus == 'SOLD_OUT':
            eventClass = ' event-sold-out'
            registerButtonClass = 'btn-default'
            registerButtonText = 'Sold out'

        startDate = datetime.strptime(
            event['start']['local'], "%Y-%m-%dT%H:%M:%S")
        endDate = datetime.strptime(event['end']['local'], "%Y-%m-%dT%H:%M:%S")

        month = monthNames[startDate.month - 1][:3].upper()
        day = startDate.day
        eventStart = startDate.hour
        eventEnd = endDate.hour
        eventName = event['name']['text']
        eventDescription = event['description']['text']

        eventStartAmPm = "am"
        eventEndAmPm = "am"

        if eventStart > 12:
            eventStart -= 12
            eventStartAmPm = "pm"

        if eventEnd > 12:
            eventEnd -= 12
            eventEndAmPm = "pm"

        url = event["url"]

        eventHtml = eventTemplate \
            .replace("`month`", month) \
            .replace("`day`", str(day)) \
            .replace("`eventStart`", str(eventStart)) \
            .replace("`eventStartAmPm`", eventStartAmPm) \
            .replace("`eventEnd`", str(eventEnd)) \
            .replace("`eventEndAmPm`", eventEndAmPm) \
            .replace("`eventName`", eventName) \
            .replace("`eventDescription`", eventDescription) \
            .replace("`eventId`", eventId) \
            .replace("`url`", url) \

        content += eventHtml

    if content == "":
        content = "<p>We don't have any events scheduled at the moment. Ask on Slack if you'd like us to arrange one.</p>"

    content = preevent + content + postevent

    return {'statusCode': 200, 'content': content}
