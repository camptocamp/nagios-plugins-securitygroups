#!/usr/bin/env python

from datetime import datetime
import argparse
import boto3
import sys
import time

class sg_public:
    def __init__(self, args):

        self.__debug   = args.debug
        self.__profile = args.profile
        self.__region  = args.region
        self.__port    = args.port
        self.__sgid    = args.security_group_id

        session = boto3.session.Session(
                profile_name = self.__profile,
                region_name  = self.__region
                )

        self.__pub_ips= []
        self.__sg_eips = []

        self.out_status = 0
        self.out_msg = 'SG: no deprecated EIP listed'

        self.__ec2_client = session.client('ec2')

        self.__get_security_groups()
        self.__get_instances()
        self.__check()


    def __print(self, string, level=1):
        '''
        Simple "print" wrapper: sends to stdout if debug is > 0
        '''
        if level <= self.__debug:
            print string

    def __get_security_groups(self):
        '''
        Get specified security group
        '''
        self.__print('Getting security groups')
        sg = self.__ec2_client.describe_security_groups(
                GroupIds=[self.__sgid]
                )
        sg = sg['SecurityGroups'][0]
        for item in sg['IpPermissions']:
            if item['FromPort'] != self.__port and item['ToPort'] != self.__port:
                continue
            for ip in item['IpRanges']:
                self.__sg_eips.append(ip['CidrIp'].split('/')[0])

    def __get_instances(self):
        '''
        Get all instances and fetch PublicIp if present
        '''
        self.__print('Getting all instances')
        reservations = self.__ec2_client.describe_instances(
                Filters=[
                    {
                        'Name': 'dns-name',
                        'Values': ['ec2*'],
                        }
                    ]
                )
        for instances in reservations['Reservations']:
            for instance in instances['Instances']:
                self.__pub_ips.append(instance['PublicIpAddress'])



    def __check(self):
        '''
        Ensure no useless directory is present on the bucket
        '''
        diff = list(set(self.__sg_eips) - set(self.__pub_ips))
        if (len(diff) != 0):
            self.out_msg = '%i Deprecated openings found' % len(diff)
            self.out_status = 2
            for i in diff:
                self.__print(i)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check if there are unused public IP opening in specified SG')
    parser.add_argument('--debug',  '-d',   help='Set verbosity level.', default=0, type=int)
    parser.add_argument('--profile', '-p', help='Pass AWS profile name.', default='default')
    parser.add_argument('--region', '-r',   help='Set AWS region.', default='eu-west-1')
    parser.add_argument('--port', '-P',   help='Specify port.', default=25, type=int)
    parser.add_argument('--security-group-id', '-s', help='', required=True)

    args = parser.parse_args()

    worker = sg_public(args)
    print worker.out_msg
    sys.exit(worker.out_status)
