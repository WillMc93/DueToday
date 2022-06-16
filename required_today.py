
# Standard
import json
import datetime
from datetime import datetime as dt

# PyPI
import jinja2 
import pandas as pd

# Local
from IssuetrakAPI import IssuetrakAPI


# Initialize Globals
# Paths:
POST_TEMPLATE = './post_template.j2'
SEVENTEEN_SCHEDULE = './017_schedule.csv'

# Pandas settings so Will could see what he was doing on a Mac
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

# Gather all open tickets for the post.
# TODO: Try and make the request query readable
def get_tickets() -> pd.DataFrame:
	request = {
		'QuerySetDefinitions': [
			{ 
				'QuerySetIndex': 0, 'QuerySetOperator': 'AND', 'QuerySetExpressions': [
					{
						'QueryExpressionOperator': 'AND',
						'QueryExpressionOperation': 'Equal',
						'FieldName': 'Status',
						'FieldFilterValue1': 'Open',
						'FieldFilterValue2': ''
					}
				]
			}
		],
		'PageIndex': 0,
		'PageSize': 100,
		'CanIncludeNotes': False,
	}

	# Initialize API connection
	api = IssuetrakAPI.IssuetrakAPI()

	# Loop through and gather all open tickets
	tickets = []
	gathered_all = False
	total = 0
	while not gathered_all:
		# POST search request
		response = api.performPost('/issues/search/', '', json.dumps(request))

		# Convert json to python dictionary
		data = response.read()
		data = json.loads(data)

		# Get ticket data
		tickets += data['Collection']

		# Check loop status
		page_count = data['CountForPage'] # number of tickets on this 'page'
		expected_total = data['TotalCount'] # maximum number of open tickets
		total += page_count
		if total <  expected_total:
			request['PageIndex'] += 1
		else:
			gathered_all = True

	# Convert tickets to DataFrame and return
	tickets = pd.DataFrame(tickets)
	return tickets


# Get a dictionary of substatus ids
def get_substatuses() -> dict:
	# Initialize API connection
	api = IssuetrakAPI.IssuetrakAPI()

	# GET data to dictionary
	response = api.performGet('/substatuses')
	data = response.read()
	data = json.loads(data)

	# Get IDs and their labels into a dictionary
	total = data['TotalCount']
	substatuses = data['Collection']
	substatuses = {id_['SubStatusID']: id_['SubStatusName'] for id_ in substatuses}
	assert(total == len(substatuses))

	return substatuses


# Get a dictionary of IssueTypeIDs
def get_issuetypes() -> dict:
	# Initialize API connection
	api = IssuetrakAPI.IssuetrakAPI()

	# GET data to dictionary
	response = api.performGet('/issuetypes')
	data = response.read()
	data = json.loads(data)

	# Get IDs and their labels into a dictionary
	total = data['TotalCount']
	issuetypes = data['Collection']
	issuetypes = {id_['IssueTypeID']: id_['IssueTypeName'] for id_ in issuetypes}
	assert(total == len(issuetypes))

	return issuetypes


# Trim to neccessary columns, apply human-readable labels, and then filter tickets for the morning post
def process_tickets(tickets:pd.DataFrame) -> pd.DataFrame:
	# Filter down to needed columns
	columns = ['IssueNumber', 'SubmittedDate', 'Subject', 'IssueTypeID',
			   'AssignedTo', 'SubStatusID', 'RequiredByDate']
	tickets = tickets.loc[:, tickets.columns.intersection(columns)]

	# Apply proper labels to SubStatusID
	substatuses = get_substatuses()
	tickets.loc[:, 'SubStatusID'] = tickets['SubStatusID'].transform(lambda x: substatuses[x])	

	# Apply proper labels to IDs in IssueTypeID
	issuetypes = get_issuetypes()
	tickets.loc[:, 'IssueTypeID'] = tickets['IssueTypeID'].transform(lambda x: issuetypes[x])

	# Make AssignedTo uniform and make it work with Teams mentions (make it an email)
	make_email = lambda user: ''.join([user.lower(), '@auburn.edu'])
	tickets.loc[:, 'AssignedTo'] = tickets['AssignedTo'].transform(lambda x: make_email(x) if x is not None else 'None')

	# Convert dates to datetime objects
	tickets.loc[:, 'SubmittedDate'] = tickets['SubmittedDate'].transform(lambda x: pd.to_datetime(x, format='%Y-%m-%dT%H:%M:%S'))
	tickets.loc[:, 'SubmittedDate'] = tickets['SubmittedDate'].transform(lambda x: x.date())
	tickets.loc[:, 'RequiredByDate'] = tickets['RequiredByDate'].transform(lambda x: pd.to_datetime(x, format='%Y-%m-%dT%H:%M:%S'))
	tickets.loc[:, 'RequiredByDate'] = tickets['RequiredByDate'].transform(lambda x: x.date())

	# Select rows for the post
	# Don't ping Adam. He's got this.
	tickets = tickets[tickets['IssueTypeID'] != 'Systems Administration']

	# Get just the scheduled tickets
	tickets = tickets[tickets['SubStatusID'].isin(['Scheduled'])]

	return tickets


# Extract dates from tickets, extract assignments from tickets, extract subject, and format nicely
def format_tickets(tickets: pd.DataFrame) -> [str]:
	# Get all tickets that are due today
	today = dt.today().date()
	tickets = tickets[tickets['RequiredByDate'] == today]

	# Format tickets into a list of strings
	formated_tickets = []
	for idx, tickie in tickets.iterrows():
		technician = tickie['AssignedTo']
		subject = tickie['Subject']
		number = tickie['IssueNumber']
		issue_string = f'{number} - <at>{technician}</at> {subject}'
		formated_tickets.append(issue_string)

	return formated_tickets


# Create the necessary html string for posting in Teams
def render_post() -> str:

	pass

# 'Script' that this script achieves
def main():
	# Get necessary info
	tickies = get_tickets()

	# Process and sort tickets
	tickies = process_tickets(tickies)
	tickies = format_tickets(tickies)
	print(tickies)

	# Generate the post
	post = render_post()

	# Print the post for copying
	print(post)


if __name__ == '__main__':
	main()
