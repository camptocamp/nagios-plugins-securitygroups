#!/usr/bin/env python

from datetime import datetime
import argparse
import boto3
import sys
import time

class sg_world:
    def __init__(self, args):

        self.__debug   = args.debug
        self.__profile = args.profile
        self.__region  = args.region
        self.__filter  = args.filters.split(',')
        self.__ports   = map(int, args.ports.split(','))

        session = boto3.session.Session(
                profile_name = self.__profile,
                region_name  = self.__region
                )

        self.__sgs = {}

        self.out_status = 0
        self.out_msg = 'SG: no world-opened stuff'

        self.__ec2_client = session.client('ec2')

        self.__get_security_groups()
        self.__check()


    def __print(self, string, level=1):
        '''
        Simple "print" wrapper: sends to stdout if debug is > 0
        '''
        if level <= self.__debug:
            print string

    def __get_security_groups(self):
        '''
        Get all Security Groups, and push only those with 0.0.0.0/0 authorized ingresses
        '''
        self.__print('Getting security groups')
        sgs = self.__ec2_client.describe_security_groups()
        for sg in sgs['SecurityGroups']:
            if sg['GroupId'] in self.__filter:
                continue
            if len(sg['IpPermissions']) > 0:
                for item in sg['IpPermissions']:
                    if len(item['IpRanges']) > 0 and \
                        item['IpRanges'][0]['CidrIp'] == '0.0.0.0/0' and \
                        (
                                item['FromPort'] in self.__ports or \
                                item['ToPort'] in self.__ports
                        ):
                        self.__print('OPENED: %i-%i %s %s' % (item['FromPort'], item['ToPort'], sg['GroupId'], sg['GroupName']))
                        if sg['GroupId'] not in self.__sgs.keys():
                            self.__sgs[sg['GroupId']] = []
                        self.__sgs[sg['GroupId']].append((item['FromPort'], item['ToPort']))


    def __check(self):
        '''
        Ensure no useless directory is present on the bucket
        '''
        if (len(self.__sgs) != 0):
            self.out_msg = 'World opened security groups found'
            self.out_status = 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check if there are opened security groups')
    parser.add_argument('--debug',  '-d',   help='Set verbosity level.', default=0, type=int)
    parser.add_argument('--profile', '-p', help='Pass AWS profile name.', default='default')
    parser.add_argument('--region', '-r',   help='Set AWS region.', default='eu-west-1')
    parser.add_argument('--ports', '-P', help='List ports to be checked (port1,port2,port3,...).', default='22,80,443,5432')
    parser.add_argument('--filters', '-F', help='Coma separated list of security groups ID to ignore (sg1,sg2,sg3,...).', default='')

    args = parser.parse_args()

    worker = sg_world(args)
    print worker.out_msg
    sys.exit(worker.out_status)
