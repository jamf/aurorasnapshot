# AWS Aurora Cluster Snapshot Handler
Allows to create and delete Aurora DB snapshots based on tags.

## USAGE
```
rdsbkp.py action tag expiration
```

## Required arguments:
```
 action           Must be backup (take snapshots) or cleanup (delete old snapshots)
 tag              DBCluster tag, can't have spaces or tabs
```

## Optional arguments:
```
 expiration       Number of days used to mark snapshots as expired and delete them (Default: 30)
```

## Requirements:

 - boto3 (pip install boto3)
 - AWS credentials configured (More information: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html)

## Limitations:
 - This script works just with Aurora DB clusters
 - AWS CLI has a limit of 100 entries per command so the script is not able to list more than 100 snapshots per cluster