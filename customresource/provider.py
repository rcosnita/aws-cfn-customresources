#!/usr/bin/env python3

# Copyright <YEAR> <COPYRIGHT HOLDER>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.'''

import argparse
import boto3
from botocore.exceptions import ClientError
import docker
import logging
import json
import urllib
import time

class CustomResource(object):
  '''Provides an example of a cfn custom resource lifecycle implementation. It artifically
  introduces a random slowness and sends some results back to CFN stack.'''

  @property
  def cfn_input_queue(self):
    return self._cfn_queue

  def __init__(self, cfn_queue, batch_size=10, visibility_timeout=10):
    logging.info('Starting the custom resource provider')
    self._cfn_queue = cfn_queue
    self._batch_size = batch_size
    self._visibility_timeout = visibility_timeout
    self._docker_cli = docker.from_env()

    self._handlers = {
      'create': self._create_resource,
      'delete': self._delete_resource
    }

  def start(self):
    '''Provides the algorithm for continuously fetching events from sqs and executing the correct
    lifecycle method. In order to find out more about the requests and possible responses the code
    might return please read:

    * https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-requests.html
    * https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-responses.html
    '''

    logging.info('Starting to consume messages from queue: {}'.format(self._cfn_queue))
    sqs_client = boto3.client('sqs')
    running = True
    msgs = None

    while running:
      try:
          msgs = sqs_client.receive_message(QueueUrl=self._cfn_queue,
                                            MaxNumberOfMessages=self._batch_size,
                                            WaitTimeSeconds=0,
                                            VisibilityTimeout=self._visibility_timeout)

          if 'Messages' in msgs:
            for msg in msgs['Messages']:
              logging.debug('Processing a new message: {}'.format(msg))
              msg_id = msg['MessageId']
              msg_handle = msg['ReceiptHandle']
              msg_body = json.loads(msg['Body'])
              msg_type = msg_body['RequestType'].lower()

              self._handlers[msg_type](msg_id, msg_body)

              logging.debug('Finished processing message: {}'.format(msg_id))
              sqs_client.delete_message(QueueUrl=self._cfn_queue, ReceiptHandle=msg_handle)

          time.sleep(5)
      except ClientError as e:
        logging.error(e)

  def _create_resource(self, msg_id, msg_body):
    '''Provides the logic for creating a new custom resource.'''

    logging.info('Creating a new resource for message {} with body {}'.format(msg_id, msg_body))

    container = self._docker_cli.containers.run('alpine',
                                                'echo \'{"Result1": "sample result 1", "Result2": "sample json result 2"}\'',
                                                detach=False)
    outputs = self._extract_output(container)

    logging.info('Notifying cloudformation about successful resource creation {}'.format(msg_id))
    s3_url = msg_body['ResponseURL']
    response = json.dumps({
      'Status': 'SUCCESS',
      'PhysicalResourceId': msg_body['ResourceProperties']['ResourceName'],
      'StackId': msg_body['StackId'],
      'RequestId': msg_body['RequestId'],
      'LogicalResourceId': msg_body['LogicalResourceId'],
      'Data': {
          'Result': outputs['Result1'],
          'Result2': outputs['Result2']
      }
    })

    self._submit_response(s3_url, response)

    logging.info('Resource created successfully: {}'.format(msg_id))

  def _delete_resource(self, msg_id, msg_body):
    '''Provides the logic for deleting a new custom resource.'''

    logging.info('Deleting existing resource for message {} with body {}'.format(msg_id, msg_body))
    logging.info('Notifying cloudformation about successful resource deletion {}'.format(msg_id))

    s3_url = msg_body['ResponseURL']
    response = json.dumps({
      'Status': 'SUCCESS',
      'PhysicalResourceId': msg_body['ResourceProperties']['ResourceName'],
      'StackId': msg_body['StackId'],
      'RequestId': msg_body['RequestId'],
      'LogicalResourceId': msg_body['LogicalResourceId'],
      "Data": {
          "Result": "CustomResult"
      }
    })

    self._submit_response(s3_url, response)

  def _submit_response(self, s3_url, response):
    '''Provides a helper method for submitting the given reponse to an S3 signed url.'''

    req = urllib.request.Request(s3_url,
                                headers={'Content-Type': ''},
                                data=bytes(response, 'utf-8'),
                                method='PUT')
    with urllib.request.urlopen(req) as f:
      print(f.read().decode('utf-8'))

  def _extract_output(self, resource_logs):
    '''Extracts the output which must be returned to the cloudformation.'''

    return json.loads(resource_logs)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(
    description='Process the command line arguments for creating the custom resource provider.')
  parser.add_argument('-l', '--logging-level', required=True,
    help='Specifies the log level used by the custom resource provider.')
  parser.add_argument('-c', '--cfn-queue', required=True,
    help='Specifies the sqs queue to listen to for communicating with the parent CFN stack.')

  args = parser.parse_args()
  log_level = getattr(logging, args.logging_level.upper())
  logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

  logging.warning('Configured logging to level {}'.format(log_level))
  CustomResource(args.cfn_queue).start()
