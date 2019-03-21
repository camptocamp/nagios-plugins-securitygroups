#!/usr/bin/env python

from datetime import datetime
import argparse
import boto3
import sys
import time

class unused_sg:
    def __init__(self, args):

        self.__debug   = args.debug
        self.__profile = args.profile
        self.__region  = args.region
        self.__clean   = args.clean
        self.__filters = args.filters.split(',')

        session = boto3.session.Session(
                profile_name = self.__profile,
                region_name  = self.__region
                )

        self.__sgs = {}
        self.__sg_instances = []

        self.out_status = 0
        self.out_msg = 'SG: no unused SG'

        self.__ec2_client = session.client('ec2')
        self.__elb_client = session.client('elb')
        self.__elbv2_client = session.client('elbv2')

        self.__get_security_groups()
        self.__get_instances_groups()
        self.__get_elbs_groups()
        self.__get_elbv2s_groups()
        self.__sg_instances = [item for sublist in self.__sg_instances for item in sublist]
        if self.__clean:
            self.__clean_sgs()
        else:
            self.__check()


    def __print(self, string, level=1):
        '''
        Simple "print" wrapper: sends to stdout if debug is > 0
        '''
        if level <= self.__debug:
            print string

    def __get_security_groups(self):
        '''
        Get all Security Groups
        '''
        self.__print('Getting security groups')
        sgs = self.__ec2_client.describe_security_groups()
        for sg in sgs['SecurityGroups']:
            if sg['GroupName'] == 'default':
                continue
            self.__sgs[sg['GroupId']] = sg['GroupName']

    def __get_instances_groups(self):
        '''
        List all security groups associated to instances
        '''
        self.__print('Getting instances')
        reservations = self.__ec2_client.describe_instances(
                MaxResults=200,
                Filters=[
                    {
                        'Name': 'instance-state-name',
                        'Values': [
                            'running',
                            'shutting-down',
                            'stopping',
                            'stopped',
                            ],
                        },
                    ]
                )
        for reservation in reservations['Reservations']:
            for instance in reservation['Instances']:
                self.__sg_instances.append([x['GroupId'] for x in instance['SecurityGroups']])


    def __get_elbs_groups(self):
        '''
        List all Security groups associated to ELBs
        '''
        self.__print('Getting ELBs')
        elbs = self.__elb_client.describe_load_balancers()
        for elb in elbs['LoadBalancerDescriptions']:
            self.__sg_instances.append(elb['SecurityGroups'])

    def __get_elbv2s_groups(self):
        '''
        List all Security groups associated to ELBv2s (aka ALB and NLB)
        '''
        self.__print('Getting ELBv2s')
        elbv2s = self.__elbv2_client.describe_load_balancers()
        for elb in elbv2s['LoadBalancers']:
            if elb['Type'] == 'application':
                self.__sg_instances.append(elb['SecurityGroups'])


    def __check(self):
        '''
        Ensure no unused security group is present
        '''
        diff = list(set(self.__sgs.keys()) - set(self.__sg_instances) - set(self.__filters))
        if (len(diff) != 0):
            self.out_msg = '%i Unused security groups found' % len(diff)
            self.out_status = 2
            self.__print('%s'% ",\n".join([ '%s %s'%(self.__sgs[i], i) for i in diff]))

    def __clean_sgs(self):
        diff = list(set(self.__sgs.keys()) - set(self.__sg_instances))
        for sg in diff:
            self.__print('Deleting %s %s' %(self.__sgs[sg], sg))
            self.__ec2_client.delete_security_group(
                    GroupId=sg,
                    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check if there are opened security groups')
    parser.add_argument('--debug',  '-d',   help='Set verbosity level.', default=0, type=int)
    parser.add_argument('--profile', '-p', help='Pass AWS profile name.', default='default')
    parser.add_argument('--region', '-r',   help='Set AWS region.', default='eu-west-1')
    parser.add_argument('--clean',  help='Clean unused security groups', action='store_const', const=True)
    parser.add_argument('--filters', '-F', help='Coma separated list of security groups ID to ignore (sg1,sg2,sg3,...).', default='')

    args = parser.parse_args()

    worker = unused_sg(args)
    print worker.out_msg
    sys.exit(worker.out_status)
