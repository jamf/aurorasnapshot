# AWS Aurora Cluster Snapshot Handler
Allows to create and delete Aurora DB Snapshots based in tags.

## USAGE
```
rdsbkp.py action tag expiration
```

## Required arguments:
```
 action           Must be backup or cleanup
 tag              DBCluster tag, can't have spaces or tabs
```

## Optional arguments:
```
 expiration       Number of days used to mark snaphosts as expired and delete them (Default: 30)
```

## Requirements:

 - boto3 (pip install boto3)
 - AWS credentials configured (More information: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html)

## Limiatations:
 - This script works just with Aurora DB Clusters
 - AWS CLI has a limit of 100 entries per command so the script is not able to list more than 100 snapshots per Cluster