# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2018, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

import os
import glob
import shutil
import unittest

import ait.core
from ait.dsn.cfdp.cfdp import read_incoming_pdu, write_outgoing_pdu
from ait.dsn.cfdp.pdu import Header, Metadata, EOF, FileData, ACK, NAK, Finished
from ait.dsn.cfdp.primitives import ConditionCode, TransactionStatus, DirectiveCode, FinishedPduFileStatus


TEST_DIRECTORY = os.path.join(os.path.dirname(__file__), '.pdusink')
def setUpModule():
    if not os.path.exists(TEST_DIRECTORY):
        os.makedirs(TEST_DIRECTORY)

def tearDownModule():
    if os.path.exists(TEST_DIRECTORY):
        shutil.rmtree(TEST_DIRECTORY)


class HeaderTest(unittest.TestCase):

    def setUp(self):
        hdr = {
            'version': 1,
            'pdu_type': 0,
            'direction': 0,
            'transmission_mode': 1,
            'crc_flag': 0,
            'pdu_data_field_length': 25,
            'source_entity_id': 123,
            'transaction_id': 1,
            'destination_entity_id': 124
        }
        self.fixture = Header(**hdr)

    def tearDown(self):
        self.fixture = None
        for f in glob.glob(os.path.join(TEST_DIRECTORY, '*')):
            os.remove(f)

    def test_header_encoding_decoding(self):
        """Convert header to bytes and then back into an object"""
        self.fixture.is_valid()
        pdu_bytes = self.fixture.to_bytes()
        pdu_object = Header.to_object(pdu_bytes)

        self.assertEqual(self.fixture.version, pdu_object.version)
        self.assertEqual(self.fixture.pdu_type, pdu_object.pdu_type)
        self.assertEqual(self.fixture.direction, pdu_object.direction)
        self.assertEqual(self.fixture.crc_flag, pdu_object.crc_flag)
        self.assertEqual(self.fixture.pdu_data_field_length, pdu_object.pdu_data_field_length)
        self.assertEqual(self.fixture.source_entity_id, pdu_object.source_entity_id)
        self.assertEqual(self.fixture.transaction_id, pdu_object.transaction_id)
        self.assertEqual(self.fixture.destination_entity_id, pdu_object.destination_entity_id)

    def test_header_read_write(self):
        """Write header to file, then read back to object"""
        self.fixture.is_valid()
        test_file = 'test_hdr.pdu'
        full_file_path = os.path.join(TEST_DIRECTORY, test_file)

        # write header to file
        write_outgoing_pdu(self.fixture, pdu_filename=test_file, output_directory=TEST_DIRECTORY)

        # read header from file
        pdu_object = None
        with open(full_file_path, 'rb') as pdu_file:
            bytes = pdu_file.read()
            pdu_bytes = [b for b in bytearray(bytes)]
            pdu_object = Header.to_object(pdu_bytes)

        self.assertNotEqual(pdu_object, None)
        self.assertEqual(self.fixture.version, pdu_object.version)
        self.assertEqual(self.fixture.pdu_type, pdu_object.pdu_type)
        self.assertEqual(self.fixture.direction, pdu_object.direction)
        self.assertEqual(self.fixture.crc_flag, pdu_object.crc_flag)
        self.assertEqual(self.fixture.pdu_data_field_length, pdu_object.pdu_data_field_length)
        self.assertEqual(self.fixture.source_entity_id, pdu_object.source_entity_id)
        self.assertEqual(self.fixture.transaction_id, pdu_object.transaction_id)
        self.assertEqual(self.fixture.destination_entity_id, pdu_object.destination_entity_id)


class MetadataTest(unittest.TestCase):

    def setUp(self):
        hdr = {
            'version': 1,
            'pdu_type': 0,
            'direction': 0,
            'transmission_mode': 1,
            'crc_flag': 0,
            'pdu_data_field_length': 25,
            'source_entity_id': 123,
            'transaction_id': 1,
            'destination_entity_id': 124
        }
        md = {
            'segmentation_control': Metadata.SEGMENTATION_CONTROL_BOUNDARIES_NOT_RESPECTED,
            'file_size': 2000,
            'source_path': '/path/to/source/file',
            'destination_path': '/path/to/destination/file'
        }
        self.fixture = Metadata(**md)
        self.fixture.header = Header(**hdr)

    def tearDown(self):
        self.fixture = None
        for f in glob.glob(os.path.join(TEST_DIRECTORY, '*')):
            os.remove(f)

    def test_md_encoding_decoding(self):
        """Convert MD to bytes and then back into an object"""
        self.fixture.is_valid()
        pdu_bytes = self.fixture.to_bytes()[self.fixture.header.length:]
        pdu_object = Metadata.to_object(pdu_bytes)

        self.assertEqual(self.fixture.segmentation_control, pdu_object.segmentation_control)
        self.assertEqual(self.fixture.file_size, pdu_object.file_size)
        self.assertEqual(self.fixture.source_path, pdu_object.source_path)
        self.assertEqual(self.fixture.destination_path, pdu_object.destination_path)

    def test_md_read_write(self):
        """Write MD to file, then read back to object"""
        self.fixture.is_valid()
        test_file = 'test_md.pdu'
        full_file_path = os.path.join(TEST_DIRECTORY, test_file)

        # write header to file
        write_outgoing_pdu(self.fixture, pdu_filename=test_file, output_directory=TEST_DIRECTORY)

        # read header from file
        pdu_object = None
        with open(full_file_path, 'rb') as pdu_file:
            bytes = pdu_file.read()
            pdu_object = read_incoming_pdu(bytes)

        self.assertNotEqual(pdu_object, None)
        self.assertEqual(self.fixture.segmentation_control, pdu_object.segmentation_control)
        self.assertEqual(self.fixture.file_size, pdu_object.file_size)
        self.assertEqual(self.fixture.source_path, pdu_object.source_path)
        self.assertEqual(self.fixture.destination_path, pdu_object.destination_path)


class EOFTest(unittest.TestCase):

    def setUp(self):
        hdr = {
            'version': 1,
            'pdu_type': 0,
            'direction': 0,
            'transmission_mode': 1,
            'crc_flag': 0,
            'pdu_data_field_length': 25,
            'source_entity_id': 123,
            'transaction_id': 1,
            'destination_entity_id': 124
        }
        eof = {
            'condition_code': ConditionCode.NO_ERROR,
            'file_checksum': 12018735385,
            'file_size': 2342
        }
        self.fixture = EOF(**eof)
        self.fixture.header = Header(**hdr)

    def tearDown(self):
        self.fixture = None
        for f in glob.glob(os.path.join(TEST_DIRECTORY, '*')):
            os.remove(f)

    def test_eof_encoding_decoding(self):
        """Convert EOF to bytes and then back into an object"""
        self.fixture.is_valid()
        eof_bytes = self.fixture.to_bytes()[self.fixture.header.length:]
        pdu_object = EOF.to_object(eof_bytes)

        limit_checksum = int(format(self.fixture.file_checksum, '>032b')[-32:], 2)
        self.assertEqual(self.fixture.condition_code, pdu_object.condition_code)
        self.assertEqual(limit_checksum, pdu_object.file_checksum)
        self.assertEqual(self.fixture.file_size, pdu_object.file_size)

    def test_eof_read_write(self):
        """Write EOF to file, then read back to object"""
        self.fixture.is_valid()
        test_file = 'test_eof.pdu'
        full_file_path = os.path.join(TEST_DIRECTORY, test_file)

        # write header to file
        write_outgoing_pdu(self.fixture, pdu_filename=test_file, output_directory=TEST_DIRECTORY)

        # read header from file
        pdu_object = None
        with open(full_file_path, 'rb') as pdu_file:
            bytes = pdu_file.read()
            pdu_object = read_incoming_pdu(bytes)

        limit_checksum = int(format(self.fixture.file_checksum, '>032b')[-32:], 2)
        self.assertNotEqual(pdu_object, None)
        self.assertEqual(self.fixture.condition_code, pdu_object.condition_code)
        self.assertEqual(limit_checksum, pdu_object.file_checksum)
        self.assertEqual(self.fixture.file_size, pdu_object.file_size)


class ACKTest(unittest.TestCase):

    def setUp(self):
        hdr = {
            'version': 1,
            'pdu_type': 0,
            'direction': 0,
            'transmission_mode': 1,
            'crc_flag': 0,
            'pdu_data_field_length': 25,
            'source_entity_id': 123,
            'transaction_id': 1,
            'destination_entity_id': 124
        }
        ack = {
            'directive_code': DirectiveCode.EOF_PDU,
            'directive_subtype_code': 0000,
            'condition_code': ConditionCode.NO_ERROR,
            'transaction_status': TransactionStatus.ACTIVE,
        }
        self.fixture = ACK(**ack)
        self.fixture.header = Header(**hdr)

    def tearDown(self):
        self.fixture = None
        for f in glob.glob(os.path.join(TEST_DIRECTORY, '*')):
            os.remove(f)

    def test_ack_encoding_decoding(self):
        """Convert ACK to bytes and then back into an object"""
        self.fixture.is_valid()
        ack_bytes = self.fixture.to_bytes()[self.fixture.header.length:]
        pdu_object = ACK.to_object(ack_bytes)

        self.assertEqual(self.fixture.directive_code, pdu_object.directive_code)
        self.assertEqual(self.fixture.directive_subtype_code, pdu_object.directive_subtype_code)
        self.assertEqual(self.fixture.condition_code, pdu_object.condition_code)
        self.assertEqual(self.fixture.transaction_status, pdu_object.transaction_status)

    def test_ack_read_write(self):
        """Write ACK to file, then read back to object"""
        self.fixture.is_valid()
        test_file = 'test_ack.pdu'
        full_file_path = os.path.join(TEST_DIRECTORY, test_file)

        # write header to file
        write_outgoing_pdu(self.fixture, pdu_filename=test_file, output_directory=TEST_DIRECTORY)

        # read header from file
        pdu_object = None
        with open(full_file_path, 'rb') as pdu_file:
            bytes = pdu_file.read()
            pdu_object = read_incoming_pdu(bytes)

        self.assertEqual(self.fixture.directive_code, pdu_object.directive_code)
        self.assertEqual(self.fixture.directive_subtype_code, pdu_object.directive_subtype_code)
        self.assertEqual(self.fixture.condition_code, pdu_object.condition_code)
        self.assertEqual(self.fixture.transaction_status, pdu_object.transaction_status)


class NAKTest(unittest.TestCase):

    def setUp(self):
        hdr = {
            'version': 1,
            'pdu_type': 0,
            'direction': 0,
            'transmission_mode': 1,
            'crc_flag': 0,
            'pdu_data_field_length': 25,
            'source_entity_id': 123,
            'transaction_id': 1,
            'destination_entity_id': 124
        }
        nak = {
            'start_of_scope': 2343,
            'end_of_scope': 2346,
            'segment_requests': [(0, 9), (12, 20)]
        }
        self.fixture = NAK(**nak)
        self.fixture.header = Header(**hdr)

    def tearDown(self):
        self.fixture = None
        for f in glob.glob(os.path.join(TEST_DIRECTORY, '*')):
            os.remove(f)

    def test_nak_encoding_decoding(self):
        """Convert NAK to bytes and then back into an object"""
        self.fixture.is_valid()
        nak_bytes = self.fixture.to_bytes()[self.fixture.header.length:]
        pdu_object = NAK.to_object(nak_bytes)

        self.assertEqual(self.fixture.start_of_scope, pdu_object.start_of_scope)
        self.assertEqual(self.fixture.end_of_scope, pdu_object.end_of_scope)
        self.assertItemsEqual(self.fixture.segment_requests, pdu_object.segment_requests)

    def test_nak_read_write(self):
        """Write NAK to file, then read back to object"""
        self.fixture.is_valid()
        test_file = 'test_nak.pdu'
        full_file_path = os.path.join(TEST_DIRECTORY, test_file)

        # write header to file
        write_outgoing_pdu(self.fixture, pdu_filename=test_file, output_directory=TEST_DIRECTORY)

        # read header from file
        pdu_object = None
        with open(full_file_path, 'rb') as pdu_file:
            bytes = pdu_file.read()
            pdu_object = read_incoming_pdu(bytes)

        self.assertNotEqual(pdu_object, None)
        self.assertEqual(self.fixture.start_of_scope, pdu_object.start_of_scope)
        self.assertEqual(self.fixture.end_of_scope, pdu_object.end_of_scope)
        self.assertItemsEqual(self.fixture.segment_requests, pdu_object.segment_requests)


class FinishedTest(unittest.TestCase):

    def setUp(self):
        hdr = {
            'version': 1,
            'pdu_type': 0,
            'direction': 0,
            'transmission_mode': 1,
            'crc_flag': 0,
            'pdu_data_field_length': 25,
            'source_entity_id': 123,
            'transaction_id': 1,
            'destination_entity_id': 124
        }
        finished = {
            'condition_code': ConditionCode.NO_ERROR,
            'end_system_status': 1,
            'delivery_code': 0,
            'file_status': FinishedPduFileStatus.FILE_DISCARDED_DELIBERATELY,
        }
        self.fixture = Finished(**finished)
        self.fixture.header = Header(**hdr)

    def tearDown(self):
        self.fixture = None
        for f in glob.glob(os.path.join(TEST_DIRECTORY, '*')):
            os.remove(f)

    def test_finished_encoding_decoding(self):
        """Convert Finished to bytes and then back into an object"""
        self.fixture.is_valid()
        finished_bytes = self.fixture.to_bytes()[self.fixture.header.length:]
        pdu_object = Finished.to_object(finished_bytes)

        self.assertEqual(self.fixture.condition_code, pdu_object.condition_code)
        self.assertEqual(self.fixture.end_system_status, pdu_object.end_system_status)
        self.assertEqual(self.fixture.delivery_code, pdu_object.delivery_code)
        self.assertEqual(self.fixture.file_status, pdu_object.file_status)

    def test_finished_read_write(self):
        """Write Finished to file, then read back to object"""
        self.fixture.is_valid()
        test_file = 'test_finished.pdu'
        full_file_path = os.path.join(TEST_DIRECTORY, test_file)

        # write header to file
        write_outgoing_pdu(self.fixture, pdu_filename=test_file, output_directory=TEST_DIRECTORY)

        # read header from file
        pdu_object = None
        with open(full_file_path, 'rb') as pdu_file:
            bytes = pdu_file.read()
            pdu_object = read_incoming_pdu(bytes)

        self.assertNotEqual(pdu_object, None)
        self.assertEqual(self.fixture.condition_code, pdu_object.condition_code)
        self.assertEqual(self.fixture.end_system_status, pdu_object.end_system_status)
        self.assertEqual(self.fixture.delivery_code, pdu_object.delivery_code)
        self.assertEqual(self.fixture.file_status, pdu_object.file_status)


class FileDataTest(unittest.TestCase):

    def setUp(self):
        hdr = {
            'version': 1,
            'pdu_type': 1,
            'direction': 0,
            'transmission_mode': 1,
            'crc_flag': 0,
            'pdu_data_field_length': 25,
            'source_entity_id': 123,
            'transaction_id': 1,
            'destination_entity_id': 124
        }
        fd = {
            'segment_offset': 0,
            'data': "Hello world this is file data."
        }
        self.fixture = FileData(**fd)
        self.fixture.header = Header(**hdr)

    def tearDown(self):
        self.fixture = None
        for f in glob.glob(os.path.join(TEST_DIRECTORY, '*')):
            os.remove(f)

    def test_fd_encoding_decoding(self):
        """Convert FD to bytes and then back into an object"""
        self.fixture.is_valid()
        fd_bytes = self.fixture.to_bytes()[self.fixture.header.length:]
        pdu_object = FileData.to_object(fd_bytes)

        self.assertEqual(self.fixture.data, pdu_object.data)

    def test_fd_read_write(self):
        """Write FD to file, then read back to object"""
        self.fixture.is_valid()
        test_file = 'test_fd.pdu'
        full_file_path = os.path.join(TEST_DIRECTORY, test_file)

        # write header to file
        write_outgoing_pdu(self.fixture, pdu_filename=test_file, output_directory=TEST_DIRECTORY)

        # read header from file
        pdu_object = None
        with open(full_file_path, 'rb') as pdu_file:
            bytes = pdu_file.read()
            pdu_object = read_incoming_pdu(bytes)

        self.assertNotEqual(pdu_object, None)
        self.assertEqual(self.fixture.data, pdu_object.data)
