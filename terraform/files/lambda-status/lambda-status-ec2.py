import boto3

#define the connection
ec2 = boto3.resource('ec2')

def lambda_handler(event, context):
    # Use the filter() method of the instances collection to retrieve the game host

    filters = [{
            'Name': 'tag:Ctl',
            'Values': ['lambda']
        }
    ]
    
    #filter the instances
    instances = ec2.instances.filter(Filters=filters)
    #print("INSTANCES:", instances)
    #locate all running instances. It is supposed to be one, but there were a few in an example
    FilteredInstances = [instance.id for instance in instances]
    print("FILTERED INSTANCES:", FilteredInstances)
    
    #print the instances for logging purposes
    #print RunningInstances 
    
    #make sure there are actually instances to shut down.
    res = "have no instances"
    if len(FilteredInstances) == 1:
        #perform the shutdown
        for inst in ec2.instances.filter(InstanceIds=FilteredInstances):
            print("ipv4address:", inst.private_ip_address)
            res =f"{inst.state['Name']},{inst.private_ip_address}"
        print (res)
        return res
    else:
        print ("instance is not unique")
        return ("Notfound", "Notfound")