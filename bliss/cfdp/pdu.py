import copy
from bliss.cfdp.util import string_length_in_bytes, string_to_bytes, bytes_to_string
from bliss.cfdp.primitives import FileDirective, ConditionCode

import logging

def make_pdu_from_bytes(pdu_bytes):
    """
    Figure out which type of PDU and return the appropriate class instance
    :param pdu_bytes:
    :return:
    """
    # get header, it will ignore extra bytes that do not belong to header
    header = Header.to_object(pdu_bytes)
    pdu_body = pdu_bytes[header.length:]
    if header.pdu_type == Header.FILE_DIRECTIVE_PDU:
        # make a file directive pdu by reading the directive code and making the appropriate object
        directive_code = FileDirective(pdu_body[0])
        if directive_code == FileDirective.METADATA:
            md = Metadata.to_object(pdu_body)
            md.header = header
            return md
        elif directive_code == FileDirective.EOF:
            eof = EOF.to_object(pdu_body)
            eof.header = header
            return eof
        elif directive_code == FileDirective.FINISHED:
            pass
        elif directive_code == FileDirective.ACK:
            pass
        elif directive_code == FileDirective.NAK:
            pass
        elif directive_code == FileDirective.PROMPT:
            pass
        elif directive_code == FileDirective.KEEP_ALIVE:
            pass
    elif header.pdu_type == Header.FILE_DATA_PDU:
        fd = FileData.to_object(pdu_body)
        fd.header = header
        return fd

    # TODO for now
    return header

class PDU(object):

    def __init__(self):
        # self.header = Header()
        self._valid = False
        self._errors = None

    @property
    def length(self):
        """Byte length of Header"""
        return len(self.to_bytes())

    def is_valid(self):
        """Check if all header fields are valid length"""
        # TODO put in checks
        self._valid = True
        self._errors = None
        return self._valid

    def to_bytes(self):
        """Return array of bytes binary converted to int"""
        raise NotImplementedError

    @staticmethod
    def to_object(bytes):
        """Return PDU subclass object created from given bytes of data"""
        raise NotImplementedError


class Metadata(PDU):

    SEGMENTATION_CONTROL_BOUNDARIES_RESPECTED = 0
    SEGMENTATION_CONTROL_BOUNDARIES_NOT_RESPECTED = 1

    file_directive_code = FileDirective.METADATA

    def __init__(self, *args, **kwargs):
        super(Metadata, self).__init__()
        self.header = kwargs.get('header', None)
        self.file_transfer = kwargs.get('file_transfer', True) # TODO need to implement PDU TLV to get this
        self.segmentation_control = kwargs.get('segmentation_control', self.SEGMENTATION_CONTROL_BOUNDARIES_RESPECTED)
        self.file_size = kwargs.get('file_size', 0)
        self.source_path = kwargs.get('source_path', None)
        self.destination_path = kwargs.get('destination_path', None)

    def to_bytes(self):
        md_bytes = []

        # File directive code
        byte_1 = self.file_directive_code.value
        md_bytes.append(byte_1)

        # This is seg. control + 7 reserved 0s
        byte_2 = self.segmentation_control << 7
        md_bytes.append(byte_2)

        # bytes 3 - 6
        # 32 bits (4 bytes) of file size in all zeroes
        # convert int value to a 32 bit binary string
        file_size_binary = format(self.file_size, '>032b')
        # split it into 4 1-byte int values
        md_bytes.append(int(file_size_binary[0:8], 2))
        md_bytes.append(int(file_size_binary[8:16], 2))
        md_bytes.append(int(file_size_binary[16:24], 2))
        md_bytes.append(int(file_size_binary[24:32], 2))

        # LVs for length and file names
        # Get length of the path in bytes
        source_file_length = string_length_in_bytes(self.source_path)
        md_bytes.append(source_file_length)
        # Convert actual string to bytes
        md_bytes.extend(string_to_bytes(self.source_path))

        dest_file_length = string_length_in_bytes(self.destination_path)
        md_bytes.append(dest_file_length)
        md_bytes.extend(string_to_bytes(self.destination_path))

        if self.header:
            header_bytes = self.header.to_bytes()
            return header_bytes + md_bytes
        return md_bytes

    @staticmethod
    def to_object(pdu_bytes):
        """Return PDU subclass object created from given bytes of data"""
        if not isinstance(pdu_bytes, list):
            raise ValueError('metadata body should be a list of bytes represented as integers')

        if len(pdu_bytes) < 8:
            raise ValueError('metadata body should be at least 8 bytes long')

        if FileDirective(pdu_bytes[0]) != Metadata.file_directive_code:
            raise ValueError('file directive code is not type METADATA')

        # Extract segmentation control, which is 1 bit + 7 reserved 0s
        segmentation_control = pdu_bytes[1] >> 7

        # convert all to 8-bit strings and append to make a full 32 bit string
        file_size_binary = format(pdu_bytes[2], '>08b') \
                           + format(pdu_bytes[3], '>08b') \
                           + format(pdu_bytes[4], '>08b') \
                           + format(pdu_bytes[5], '>08b')
        file_size = int(file_size_binary, 2)

        source_file_length = pdu_bytes[6]
        start_index = 7
        end_index = start_index + source_file_length
        source_path = bytes_to_string(pdu_bytes[start_index:end_index])

        dest_file_length = pdu_bytes[end_index]
        start_index = end_index + 1
        end_index = start_index + dest_file_length
        dest_path = bytes_to_string(pdu_bytes[start_index:end_index])

        return Metadata(
            segmentation_control=segmentation_control,
            file_size=file_size,
            source_path=source_path,
            destination_path=dest_path
        )


class EOF(PDU):

    file_directive_code = FileDirective.EOF

    def __init__(self, *args, **kwargs):
        super(EOF, self).__init__()
        self.header = kwargs.get('header', None)
        self.condition_code = kwargs.get('condition_code', None)
        self.file_checksum = kwargs.get('file_checksum', 0)
        self.file_size = kwargs.get('file_size', None)

    def to_bytes(self):
        bytes = []

        # File directive code
        byte_1 = self.file_directive_code.value
        bytes.append(byte_1)

        # 4-bit condition code + 4 bit spare
        byte_2 = self.condition_code.value << 4
        bytes.append(byte_2)

        # 32 bit checksum
        checksum_binary = format(self.file_checksum, '>032b')
        bytes.append(int(checksum_binary[0:8], 2))
        bytes.append(int(checksum_binary[8:16], 2))
        bytes.append(int(checksum_binary[16:24], 2))
        bytes.append(int(checksum_binary[24:32], 2))

        # 32 bit file size in octets
        filesize_binary = format(self.file_size, '>032b')
        bytes.append(int(filesize_binary[0:8], 2))
        bytes.append(int(filesize_binary[8:16], 2))
        bytes.append(int(filesize_binary[16:24], 2))
        bytes.append(int(filesize_binary[24:32], 2))

        if self.header:
            header_bytes = self.header.to_bytes()
            return header_bytes + bytes
        return bytes

    @staticmethod
    def to_object(pdu_bytes):
        """Return PDU subclass object created from given bytes of data"""
        if not isinstance(pdu_bytes, list):
            raise ValueError('eof body should be a list of bytes represented as integers')

        if len(pdu_bytes) < 10:
            raise ValueError('eofbody should be at least 10 bytes long')

        if FileDirective(pdu_bytes[0]) != EOF.file_directive_code:
            raise ValueError('file directive code is not type EOF')

        # Extract 4 bit condition code
        condition_code = ConditionCode(pdu_bytes[1] >> 4)

        # 32 bit checksum
        # convert all to 8-bit strings and append to make a full 32 bit string
        file_checksum_binary = format(pdu_bytes[2], '>08b') \
                           + format(pdu_bytes[3], '>08b') \
                           + format(pdu_bytes[4], '>08b') \
                           + format(pdu_bytes[5], '>08b')
        file_checksum = int(file_checksum_binary, 2)

        # 32 bit file size in octets
        file_size_binary = format(pdu_bytes[6], '>08b') \
                               + format(pdu_bytes[7], '>08b') \
                               + format(pdu_bytes[8], '>08b') \
                               + format(pdu_bytes[9], '>08b')
        file_size = int(file_size_binary, 2)

        return EOF(
            condition_code=condition_code,
            file_checksum=file_checksum,
            file_size=file_size
        )


class FileData(PDU):

    def __init__(self, *args, **kwargs):
        super(FileData, self).__init__()
        self.header = kwargs.get('header', None)
        self.segment_offset = kwargs.get('segment_offset', None)
        self.data = kwargs.get('data', None)

    def to_bytes(self):
        bytes = []

        # Segment Offset is 32 bits
        byte_1 = format(self.segment_offset, '>032b')
        bytes.append(int(byte_1[0:8], 2))
        bytes.append(int(byte_1[8:16], 2))
        bytes.append(int(byte_1[16:24], 2))
        bytes.append(int(byte_1[24:32], 2))

        # Variable Length File Data
        # Get length of chunk
        data_in_bytes = string_to_bytes(self.data)
        bytes.extend(data_in_bytes)

        if self.header:
            header_bytes = self.header.to_bytes()
            return header_bytes + bytes
        return bytes

    @staticmethod
    def to_object(pdu_bytes):
        """Return PDU subclass object created from given bytes of data"""
        if not isinstance(pdu_bytes, list):
            raise ValueError('fd body should be a list of bytes represented as integers')

        if len(pdu_bytes) < 4:
            raise ValueError('eofbody should be at least 4 bytes long')

        # Extract 32 bit offset
        # convert all to 8-bit strings and append to make a full 32 bit string
        segment_offset_binary = format(pdu_bytes[0], '>08b') \
                               + format(pdu_bytes[1], '>08b') \
                               + format(pdu_bytes[2], '>08b') \
                               + format(pdu_bytes[3], '>08b')
        segment_offset = int(segment_offset_binary, 2)

        # TODO error handling if there is no file data
        file_data = None
        if len(pdu_bytes) > 4:
            # File data chunk of variable size
            file_data = bytes_to_string(pdu_bytes[4:])

        return FileData(
            segment_offset=segment_offset,
            data=file_data
        )


class Header(object):
    # Header Flag Values
    # TODO move where it makes more sense
    FILE_DIRECTIVE_PDU = 0
    FILE_DATA_PDU = 1
    TOWARDS_RECEIVER = 0
    TOWARDS_SENDER = 1
    ACK_MODE = 0
    UNACK_MODE = 1
    CRC_NOT_PRESENT = 0
    CRC_PRESENT = 1

    TRANSACTION_SEQ_NUM_LENGTH = 4

    def __init__(self, *args, **kwargs):
        """
        Representation of PDU Fixed Header
        :param version:                         3 bit; version number 000 first version
        :type version: int
        :param pdu_type:                        1 bit; '0' for File Directive, '1' for File Data
        :type pdu_type: int
        :param direction:                       1 bit; '0' for toward file receiver, '1' for toward file sender
        :type direction: int
        :param transmission_mode:               1 bit; '0' for acknowledged, '1' for unack
        :type transmission_mode: int
        :param crc_flag:                        1 bit; '0' for CRC not present; '1' for CRC present
        :type crc_flag: int
        :param pdu_data_field_length:           16 bit; length of data field in octets
        :type pdu_data_field_length: int
        :param entity_ids_length:               3 bit; number of octets in entity ID (source or destination entity) - 1. E.g. '0' mean sequence number is 1 octet
        :type entity_ids_length: int
        :param transaction_id_length:      3 bit; number of octets in sequence number - 1
        :type transaction_id_length: int
        :param source_entity_id:                variable bit; uniquely identifies the entity that originated transaction. Unsigned binary int. See entity_ids_length for length
        :type source_entity_id: str
        :param transaction_id:             variable bit; uniquely identifies the entity that originated transaction. Unsigned binary int. See transaction_id_length for length
        :type transaction_id: str
        :param destination_entity_id:              variable bit; uniquely identifies the entity that originated transaction. Unsigned binary int. See entity_ids_length for length
        :type destination_entity_id: str
        """
        # valid flag to make sure contents are valid and of appropriate length
        self._valid = False
        self._errors = None

        # store raw header
        self.version = kwargs.get('version', 0)
        self.pdu_type = kwargs.get('pdu_type', self.FILE_DIRECTIVE_PDU)
        self.direction = kwargs.get('direction', self.TOWARDS_RECEIVER)
        self.transmission_mode = kwargs.get('transmission_mode', self.UNACK_MODE)
        self.crc_flag = kwargs.get('crc_flag', self.CRC_NOT_PRESENT)
        self.pdu_data_field_length = kwargs.get('pdu_data_field_length', None)
        # self.entity_ids_length = kwargs.get('entity_ids_length', None)
        # self.transaction_id_length = kwargs.get('transaction_id_length', None)
        self.source_entity_id = kwargs.get('source_entity_id', None)
        self.transaction_id = kwargs.get('transaction_id', None)
        self.destination_entity_id = kwargs.get('destination_entity_id', None)

    def __copy__(self):
        newone = type(self)()
        newone.__dict__.update(self.__dict__)
        return newone

    @property
    def length(self):
        """Byte length of Header"""
        return len(self.to_bytes())

    def is_valid(self):
        """Check if all header fields are valid length"""
        # TODO put in checks
        self._valid = True
        self._errors = None
        return self._valid

    def to_bytes(self):
        """
        Encode PDU to a raw bytes (string) format to be transmitted

        Each byte is encoded into an int representation of the binary, and added to a list of bytes in order.
        All the bytes are then packed into a struct.
        """
        if not self.is_valid():
            raise Exception('Header contents invalid. {}'.format(self._errors))

        header_bytes = []

        # --- BYTE 1 ---
        # First byte of the header comprised of:
        #   version (3)
        #   pdu_type (1)
        #   direction (1)
        #   transmission_mode (1)
        #   crc flag (1)
        #   reserved (1) (set to 0)

        # Create hex mask to encode version in first 3 bits
        # Convert version to binary string
        # Truncate at 3 bits
        bin_version = format(self.version & 0x7, '03b')
        # Right pad to 8 bits
        bin_version = format(bin_version, '<08s')
        # Convert version encoded in first 3 bits of a byte into an integer
        version_hex_int = int(bin_version, 2)
        # Start masking rest of the byte from here
        byte_1 = version_hex_int
        if self.pdu_type == self.FILE_DATA_PDU:
            byte_1 = byte_1 | 0x10
        if self.direction == self.TOWARDS_SENDER:
            byte_1 = byte_1 | 0x08
        if self.transmission_mode == self.UNACK_MODE:
            byte_1 = byte_1 | 0x04
        if self.crc_flag == self.CRC_PRESENT:
            byte_1 = byte_1 | 0x02
        # Append first byte int value. Later we will pack a struct
        header_bytes.append(byte_1)

        # --- BYTES 2 and 3 ---
        #   PDU Data Field Length (16)
        # Split value into 2 8 bit values
        bin_pdu_length = format(self.pdu_data_field_length, '016b')
        # Convert each half to and integer and append
        header_bytes.append(int(bin_pdu_length[0:7], 2))
        header_bytes.append(int(bin_pdu_length[8:], 2))

        # --- BYTE 4 ---
        # Byte comprised of:
        #   reserved (1)
        #   entity ids length (3)
        #   reserved (1)
        #   transaction seq num length (3)

        # calculate entity id length by whichever is longer
        if self.source_entity_id > self.destination_entity_id:
            entity_id_length = string_length_in_bytes(self.source_entity_id)
        else:
            entity_id_length = string_length_in_bytes(self.destination_entity_id)

        # Number of octets in entity id less one; '0' means that entity id is one octet
        entity_id_length -= 1
        # Truncate at 3 bits and convert to 4 bit binary string (first bit should be 0 for  placeholder)
        bin_entity_id_length = format(entity_id_length & 0x7, '04b')
        bin_trans_seq_num_len = format(string_length_in_bytes(self.transaction_id) & 0x7, '04b')
        byte_4 = int(bin_entity_id_length + bin_trans_seq_num_len, 2)
        header_bytes.append(byte_4)

        # --- REMAINING BYTES ---
        # Variable in size depending on the lengths defined above
        #   source entity id (variable)
        #   transaction seq num (variable)
        #   destination entity id (variable)

        # get bytes for each value
        entity_id_binary = string_to_bytes(self.source_entity_id)
        transaction_id_binary = string_to_bytes(self.transaction_id)
        destination_id_binary = string_to_bytes(self.destination_entity_id)

        # tack on bytes to whole header bytes
        header_bytes.extend(entity_id_binary)
        header_bytes.extend(transaction_id_binary)
        header_bytes.extend(destination_id_binary)

        return header_bytes
        # pack bytes to struct
        # return struct.pack('!' + 'B' * len(header_bytes), *header_bytes)

    @staticmethod
    def to_object(pdu_hdr):
        """Return PDU subclass object created from given bytes of data"""

        if not isinstance(pdu_hdr, list):
            raise ValueError('pdu header should be a list of bytes represented as integers')

        if len(pdu_hdr) < 4:
            raise ValueError('pdu header should be at least 4 bytes long')

        # --- BYTE 1 ---
        # First byte of the header comprised of:
        # version (3), pdu_type (1), direction (1), transmission_mode (1), crc flag (1)
        byte_1 = pdu_hdr[0]
        # Mask first 3 bits and right shift 5 to get version
        version = (byte_1 & 0xe0) >> 5
        # If masked bit is > 0, it's a file data pdu. Otherwise bit is 0 and its file directive
        pdu_type = Header.FILE_DATA_PDU if (byte_1 & 0x10) else Header.FILE_DIRECTIVE_PDU
        direction = Header.TOWARDS_SENDER if (byte_1 & 0x08) else Header.TOWARDS_RECEIVER
        transmission_mode = Header.UNACK_MODE if (byte_1 & 0x04) else Header.ACK_MODE
        crc_flag = Header.CRC_PRESENT if (byte_1 & 0x02) else Header.CRC_NOT_PRESENT

        # --- BYTES 2 and 3 ---
        #   PDU Data Field Length (16)
        byte_2 = pdu_hdr[1]
        byte_3 = pdu_hdr[2]
        # left shift first byte 4 to get right position of bits
        pdu_data_length = byte_2 << 4
        pdu_data_length += byte_3

        # --- BYTE 4 ---
        # Byte comprised of:
        #   reserved (1), entity ids length (3), reserved (1), transaction seq num length (3)
        byte_4 = pdu_hdr[3]
        # mask the appropriate bits just for good measure
        entity_ids_length = (byte_4 & 0x70) >> 4
        # add one because value is "length less 1"
        entity_ids_length += 1
        transaction_id_length = byte_4 & 0x7

        # Remaining bytes, use length values above to figure out
        pdu_hdr_length = len(pdu_hdr)
        expected_length = 4 + entity_ids_length*2 + transaction_id_length
        if pdu_hdr_length < expected_length:
            raise ValueError('pdu header is not big enough to contain entity ids and trans. seq. number. '
                             'header is only {0} bytes, expected {1} bytes'.format(pdu_hdr_length, expected_length))

        # source id
        start_index = 4
        end_index = start_index + entity_ids_length
        source_entity_id = bytes_to_string(pdu_hdr[start_index:end_index])
        # go through bytes in reverse order so we can shift appropriately

        # tx seq num
        start_index = end_index
        end_index = start_index + transaction_id_length
        transaction_id = bytes_to_string(pdu_hdr[start_index:end_index])

        # destination id
        start_index = end_index
        end_index = start_index + entity_ids_length
        destination_entity_id = bytes_to_string(pdu_hdr[start_index:end_index])

        return Header(
            version=version,
            pdu_type=pdu_type,
            direction=direction,
            transmission_mode=transmission_mode,
            crc_flag=crc_flag,
            pdu_data_field_length=pdu_data_length,
            source_entity_id=source_entity_id,
            transaction_id=transaction_id,
            destination_entity_id=destination_entity_id
        )
