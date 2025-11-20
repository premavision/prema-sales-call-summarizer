from enum import Enum


class CallStatus(str, Enum):
    NEW = "NEW"
    TRANSCRIBED = "TRANSCRIBED"
    ANALYZED = "ANALYZED"
    SYNCED = "SYNCED"


class CRMSyncStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
