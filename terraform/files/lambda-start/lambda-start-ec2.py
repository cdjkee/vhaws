import boto3

#define the connection
ec2 = boto3.resource('ec2')

def lambda_handler(event, context):
    # Use the filter() method of the instances collection to retrieve the game host

    filters = [{
            'Name': 'tag:Ctl',
            'Values': ['lambda']
        },
        {
            'Name': 'instance-state-name', 
            'Values': ['stopped']
        }
    ]
    
    #filter the instances
    instances = ec2.instances.filter(Filters=filters)

    #locate all running instances. It is supposed to be one, but there were a few in an example
    StoppedInstances = [instance.id for instance in instances]
    
    #print the instances for logging purposes
    #print RunningInstances 
    
    #make sure there are actually instances to shut down. 
    if len(StoppedInstances) > 0:
        #perform the shutdown
        Starting = ec2.instances.filter(InstanceIds=StoppedInstances).start()
        print (Starting)
        return Starting
    else:
        print ("Have no running instances")