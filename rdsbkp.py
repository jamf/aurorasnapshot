#!/usr/bin/env python

import boto3
import datetime
import pprint
import time
import sys

def main():
	args = {}
	setVar(args)
	checkArgv(args)
	dbstatus = {}
	client = boto3.client('rds')
	initDB(client, dbstatus)
	if args['action'] == 'backup':
		updateTag(client, dbstatus, args['env'])
		tagChecker(dbstatus)
		backup(client, dbstatus, args['env'])
	elif args['action'] == 'cleanup':
		updateTag(client, dbstatus, args['env'])
		tagChecker(dbstatus)
		cleanup(client, dbstatus, args['env'], args['exp'])
	else:
		printHelp()
		exit(1)

##### General fuctions

def setVar(args):
	try:
		args['exp'] = int(sys.argv[3])
	except:
		args['exp'] = 30
	try:
		args['action'] = sys.argv[1]
		args['env'] = sys.argv[2]
	except IndexError:
		args['action'] = ''
		args['env'] = ''

def checkArgv(args):
	if args['action'] == '' or args['env'] == '':
		printHelp()
		exit(1)

def printHelp():
	print("""Usage: rdsbkp.py action tag expiration

Required arguments:
 action           Must be backup or cleanup
 tag              DBCluster tag, can't have spaces or tabs

Optional arguments:
 expiration       Number of days used to mark snaphosts as expired and delete them (Default: 30)

Requirements:
 - boto3 (pip install boto3)
 - AWS credentials configured (More information: 
 https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html)

Limitations:
 - This script works just with Aurora DB clusters
 - AWS CLI has a limit of 100 entries per command so the script is not able to
 list more than 100 snapshots per cluster
""")

##### Shared functions

def initDB(botoclient, db):
	dbclusters = botoclient.describe_db_clusters()
	for clusters in dbclusters['DBClusters']:
	        db[str(clusters['DBClusterIdentifier'])] = {}
	        db[str(clusters['DBClusterIdentifier'])]['status'] = 0
	        db[str(clusters['DBClusterIdentifier'])]['env'] = 0
	        db[str(clusters['DBClusterIdentifier'])]['arn'] = clusters['DBClusterArn']
	        db[str(clusters['DBClusterIdentifier'])]['snapName'] = 0

def updateTag(botoclient, db, environment):
	for keys in db.keys():
	        tags = botoclient.list_tags_for_resource(ResourceName=db[keys]['arn'])
	        if tags['TagList'] != []:
	                for envtag in tags['TagList']:
	                        if envtag['Value'] == environment:
	                                db[keys]['env'] = envtag['Value']

def tagSearcher(db):
	environment = sys.argv[2]
	return db[1]['env'] == environment

def tagChecker(db):
	count = 0
	tagdbs = filter(tagSearcher, db.items())
	for db in tagdbs:
		count += 1
	if count == 0:
		print('Tag not found')
		exit(5)

##### Backup functions

def takeSnapshot(botoclient, dbcluster):
	print('Backing up: ' + dbcluster)
	date = datetime.datetime.now().strftime("%Y-%b-%d-%H-%M-%S")
	snapName = dbcluster + "-" + date
	response = botoclient.create_db_cluster_snapshot(DBClusterSnapshotIdentifier=snapName, DBClusterIdentifier=dbcluster)
	pp = pprint.PrettyPrinter(indent=4)
	pp.pprint(response)
	return snapName

def updateSnapStatus(botoclient, db):
	response = botoclient.describe_db_cluster_snapshots(DBClusterSnapshotIdentifier=db['snapName'])
	db['status'] = response['DBClusterSnapshots'][0]['Status']

def isDone(db):
	return db[1]['status'] == 'creating'

def countWaiting(db):
	count = 0
	donedbs = filter(isDone, db.items())
	for db in donedbs:
		count += 1
	return count

def finalBackupPrint(db, environment):
	print("")
	print("--------------------- Final Status ---------------------")
	print("")
	for keys in db.keys():
		if db[keys]['env'] == environment:
			print("DB Cluster: " + str(keys) + ", Snapshot Name: " + str(db[keys]['snapName']) + ", Status: " + str(db[keys]['status']))

def finalBackupStatus(db, environment):
	for keys in db.keys():
		if db[keys]['env'] == environment and db[keys]['status'] != "creating":
			exit(5)

def backup(botoclient, db, environment):
	for keys in db.keys():
		if db[keys]['env'] == environment:
			try:
				db[keys]['snapName'] = takeSnapshot(botoclient, keys)
				updateSnapStatus(botoclient, db[keys])
			except:
				db[keys]['status'] = 'Error'
				print('Error creating snapshot of DBCluster: ' + keys)
				pass
	print('Waiting for snapshots to become available')
	waiting = 1
	while waiting:	
		for keys in db.keys():
			if db[keys]['env'] == environment and db[keys]['status'] == "creating":
				updateSnapStatus(botoclient, db[keys])
				print("DB Cluster: " + keys + ", Snapshot Name: " + db[keys]['snapName'] + ", Status: " + db[keys]['status'])
		waiting = countWaiting(db)
		time.sleep(5)
	finalBackupPrint(db, environment)
	finalBackupStatus(db, environment)

#### CleanUp functions

def initSnapDB(botoclient, dbclusters, dbsnap, environment, today):
	for keys in dbclusters.keys():
		if dbclusters[keys]['env'] == environment:
			response = botoclient.describe_db_cluster_snapshots(DBClusterIdentifier=keys, SnapshotType='manual')
			for snapshot in response['DBClusterSnapshots']:
				daysAlive = today - snapshot['SnapshotCreateTime'].date()
				dbsnap[str(snapshot['DBClusterSnapshotIdentifier'])] = daysAlive.days

def deleteSnapshot(botoclient, dbsnap, expiration):
	for snap in dbsnap:
		if dbsnap[snap] > expiration:
			print('----')
			print(snap + " is " + str(dbsnap[snap]) + " days old, so it will be deleted")
			response = botoclient.delete_db_cluster_snapshot(DBClusterSnapshotIdentifier=snap)
			pp = pprint.PrettyPrinter(indent=4)
			pp.pprint(response)

def finalCleanupPrint(dbsnap, expiration):
	print("")
	print("--------------------- Final Status ---------------------")
	print("")
	count = 0
	for snap in dbsnap.keys():
		if dbsnap[snap] > expiration:
			count += 1
			print("Deleted Snapshot Name: " + str(snap) + ", Expired: " + str(dbsnap[snap]) + " days ago.")
	if count == 0:
		print('There is no snapshots to delete')

def cleanup(botoclient, db, environment, expiration):
	snapinfo = {}
	today = datetime.datetime.today().date()
	initSnapDB(botoclient, db, snapinfo, environment, today)
	deleteSnapshot(botoclient, snapinfo, expiration)
	finalCleanupPrint(snapinfo, expiration)

main()