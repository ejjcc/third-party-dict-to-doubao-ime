#!/usr/bin/env python3
import argparse
import base64
import datetime as dt
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from wetype_leveldb import ScanStats, scan_wetype_leveldb

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SYS_DICT = Path("/Library/Input Methods/DoubaoIme.app/Contents/Frameworks/OimeEngine.framework/Versions/A/Resources/OimeEngineResources.bundle")
DEFAULT_FRAMEWORKS = Path("/Library/Input Methods/DoubaoIme.app/Contents/Frameworks")
DEFAULT_ACCOUNT_ROOT = Path.home() / "Library/Application Support/DoubaoIme/EngineUserDictAccounts"
DEFAULT_WETYPE_ROOT = Path.home() / "Library/Application Support/WeType/userDict/v5"
WETYPE_APP = Path("/Library/Input Methods/WeType.app")

EMBEDDED_HELPER_SOURCE_B64 = """
I2ltcG9ydCA8Rm91bmRhdGlvbi9Gb3VuZGF0aW9uLmg+CiNpbXBvcnQgPG9iamMvbWVzc2FnZS5oPgojaW1wb3J0IDxvYmpjL3J1bnRpbWUuaD4KI2ltcG9ydCA8ZGxmY24uaD4KI2luY2x1ZGUgPGdldG9wdC5oPgoKc3RhdGljIGlkIGNhbGwoaWQgb2JqLCBTRUwgc2VsKSB7IHJldHVybiAoKGlkICgqKShpZCwgU0VMKSlvYmpjX21zZ1NlbmQpKG9iaiwgc2VsKTsgfQpzdGF0aWMgaWQgY2FsbE9iajIoaWQgb2JqLCBTRUwgc2VsLCBpZCBhLCBpZCBiKSB7IHJldHVybiAoKGlkICgqKShpZCwgU0VMLCBpZCwgaWQpKW9iamNfbXNnU2VuZCkob2JqLCBzZWwsIGEsIGIpOyB9CnN0YXRpYyBCT09MIGNhbGxCb29sMShpZCBvYmosIFNFTCBzZWwsIGlkIGFyZykgeyByZXR1cm4gKChCT09MICgqKShpZCwgU0VMLCBpZCkpb2JqY19tc2dTZW5kKShvYmosIHNlbCwgYXJnKTsgfQpzdGF0aWMgQk9PTCBjYWxsQm9vbDMoaWQgb2JqLCBTRUwgc2VsLCBsb25nIGxvbmcgYSwgaWQgYiwgaWQgYykgeyByZXR1cm4gKChCT09MICgqKShpZCwgU0VMLCBsb25nIGxvbmcsIGlkLCBpZCkpb2JqY19tc2dTZW5kKShvYmosIHNlbCwgYSwgYiwgYyk7IH0Kc3RhdGljIHZvaWQgY2FsbFZvaWQzKGlkIG9iaiwgU0VMIHNlbCwgbG9uZyBsb25nIGEsIGlkIGIsIGlkIGMpIHsgKCh2b2lkICgqKShpZCwgU0VMLCBsb25nIGxvbmcsIGlkLCBpZCkpb2JqY19tc2dTZW5kKShvYmosIHNlbCwgYSwgYiwgYyk7IH0Kc3RhdGljIEJPT0wgY2FsbEJvb2xCb29sKGlkIG9iaiwgU0VMIHNlbCwgQk9PTCBhKSB7IHJldHVybiAoKEJPT0wgKCopKGlkLCBTRUwsIEJPT0wpKW9iamNfbXNnU2VuZCkob2JqLCBzZWwsIGEpOyB9CnN0YXRpYyB2b2lkIGNhbGxTZXRCb29sKGlkIG9iaiwgU0VMIHNlbCwgQk9PTCBhKSB7ICgodm9pZCAoKikoaWQsIFNFTCwgQk9PTCkpb2JqY19tc2dTZW5kKShvYmosIHNlbCwgYSk7IH0Kc3RhdGljIHZvaWQgY2FsbFNldE9iaihpZCBvYmosIFNFTCBzZWwsIGlkIGFyZykgeyAoKHZvaWQgKCopKGlkLCBTRUwsIGlkKSlvYmpjX21zZ1NlbmQpKG9iaiwgc2VsLCBhcmcpOyB9CgpzdGF0aWMgdm9pZCB1c2FnZShjb25zdCBjaGFyICpuYW1lKSB7CiAgICBmcHJpbnRmKHN0ZGVyciwgInVzYWdlOiAlcyAtLW1vZGUgaW1wb3J0fHZlcmlmeSAtLXN0b3JhZ2UgRElSIC0tc3lzLWRpY3QgRElSIC0tdXNlci1kaWN0IERJUiAtLWlucHV0IFRTViBbLS1zYXZlLWV2ZXJ5IE5dIFstLWV4cG9ydC1kaXIgRElSXSBbLS1wcm9ncmVzcy1ldmVyeSBOXVxuIiwgbmFtZSk7Cn0KCnN0YXRpYyBOU1N0cmluZyAqc3RyYXJnKGNvbnN0IGNoYXIgKnZhbHVlKSB7IHJldHVybiB2YWx1ZSA/IFtOU1N0cmluZyBzdHJpbmdXaXRoVVRGOFN0cmluZzp2YWx1ZV0gOiBuaWw7IH0KCnN0YXRpYyBpZCBjb252ZXJ0KGlkIGVuZ2luZSwgQ2xhc3MgcGFyYW1zQ2xhc3MsIE5TU3RyaW5nICpwaW55aW4pIHsKICAgIGlkIHBhcmFtcyA9IGNhbGwoW3BhcmFtc0NsYXNzIGFsbG9jXSwgQHNlbGVjdG9yKGluaXQpKTsKICAgIGNhbGxTZXRCb29sKHBhcmFtcywgQHNlbGVjdG9yKHNldElzU2luZ2xlV29yZE1vZGU6KSwgTk8pOwogICAgY2FsbFNldEJvb2wocGFyYW1zLCBAc2VsZWN0b3Ioc2V0U2Vzc2lvbkxMTUVuYWJsZTopLCBOTyk7CiAgICBjYWxsU2V0T2JqKHBhcmFtcywgQHNlbGVjdG9yKHNldFByZWNlZGluZ1RleHQ6KSwgQCIiKTsKICAgIHJldHVybiBjYWxsT2JqMihlbmdpbmUsIEBzZWxlY3Rvcihjb252ZXJ0OjopLCBwaW55aW4sIHBhcmFtcyk7Cn0KCnN0YXRpYyBOU0FycmF5ICpsb2FkTGluZXMoTlNTdHJpbmcgKnBhdGgpIHsKICAgIE5TRXJyb3IgKmVyciA9IG5pbDsKICAgIE5TU3RyaW5nICpjb250ZW50ID0gW05TU3RyaW5nIHN0cmluZ1dpdGhDb250ZW50c09mRmlsZTpwYXRoIGVuY29kaW5nOk5TVVRGOFN0cmluZ0VuY29kaW5nIGVycm9yOiZlcnJdOwogICAgaWYgKCFjb250ZW50KSB7CiAgICAgICAgZnByaW50ZihzdGRlcnIsICJyZWFkIGlucHV0IGZhaWxlZDogJXNcbiIsIFtbZXJyIGRlc2NyaXB0aW9uXSBVVEY4U3RyaW5nXSk7CiAgICAgICAgZXhpdCgxKTsKICAgIH0KICAgIHJldHVybiBbY29udGVudCBjb21wb25lbnRzU2VwYXJhdGVkQnlDaGFyYWN0ZXJzSW5TZXQ6W05TQ2hhcmFjdGVyU2V0IG5ld2xpbmVDaGFyYWN0ZXJTZXRdXTsKfQoKc3RhdGljIEJPT0wgY29uZmlndXJlKGlkIGVuZ2luZSwgTlNTdHJpbmcgKnN0b3JhZ2UsIE5TU3RyaW5nICpzeXMsIE5TU3RyaW5nICp1c3IpIHsKICAgIEJPT0wgc3RvcmFnZU9LID0gY2FsbEJvb2wxKGVuZ2luZSwgQHNlbGVjdG9yKHNldFN0b3JhZ2VQYXRoOiksIHN0b3JhZ2UpOwogICAgQk9PTCBjcmVhdGVkID0gY2FsbEJvb2wzKGVuZ2luZSwgQHNlbGVjdG9yKGNyZWF0ZUlucHV0RW5naW5lOnN5c0RpY3RQYXRoOnVzZXJEaWN0UGF0aDopLCAwLCBzeXMsIHVzcik7CiAgICBjYWxsVm9pZDMoZW5naW5lLCBAc2VsZWN0b3IobGF1bmNoRW5naW5lOnN5c0RpY3RQYXRoOnVzZXJEaWN0UGF0aDopLCAwLCBzeXMsIHVzcik7CiAgICBmcHJpbnRmKHN0ZGVyciwgImVuZ2luZSBzZXRTdG9yYWdlUGF0aD0lZCBjcmVhdGVJbnB1dEVuZ2luZT0lZFxuIiwgc3RvcmFnZU9LLCBjcmVhdGVkKTsKICAgIHJldHVybiBzdG9yYWdlT0sgJiYgY3JlYXRlZDsKfQoKaW50IG1haW4oaW50IGFyZ2MsIGNoYXIgKiphcmd2KSB7CiAgICBAYXV0b3JlbGVhc2Vwb29sIHsKICAgICAgICBzdGF0aWMgc3RydWN0IG9wdGlvbiBvcHRpb25zW10gPSB7CiAgICAgICAgICAgIHsibW9kZSIsIHJlcXVpcmVkX2FyZ3VtZW50LCBOVUxMLCAnbSd9LAogICAgICAgICAgICB7InN0b3JhZ2UiLCByZXF1aXJlZF9hcmd1bWVudCwgTlVMTCwgJ3MnfSwKICAgICAgICAgICAgeyJzeXMtZGljdCIsIHJlcXVpcmVkX2FyZ3VtZW50LCBOVUxMLCAnZCd9LAogICAgICAgICAgICB7InVzZXItZGljdCIsIHJlcXVpcmVkX2FyZ3VtZW50LCBOVUxMLCAndSd9LAogICAgICAgICAgICB7ImlucHV0IiwgcmVxdWlyZWRfYXJndW1lbnQsIE5VTEwsICdpJ30sCiAgICAgICAgICAgIHsic2F2ZS1ldmVyeSIsIHJlcXVpcmVkX2FyZ3VtZW50LCBOVUxMLCAnZSd9LAogICAgICAgICAgICB7ImV4cG9ydC1kaXIiLCByZXF1aXJlZF9hcmd1bWVudCwgTlVMTCwgJ3gnfSwKICAgICAgICAgICAgeyJwcm9ncmVzcy1ldmVyeSIsIHJlcXVpcmVkX2FyZ3VtZW50LCBOVUxMLCAncCd9LAogICAgICAgICAgICB7ImhlbHAiLCBub19hcmd1bWVudCwgTlVMTCwgJ2gnfSwKICAgICAgICAgICAgezAsIDAsIDAsIDB9LAogICAgICAgIH07CgogICAgICAgIE5TU3RyaW5nICptb2RlID0gbmlsOwogICAgICAgIE5TU3RyaW5nICpzdG9yYWdlID0gbmlsOwogICAgICAgIE5TU3RyaW5nICpzeXMgPSBuaWw7CiAgICAgICAgTlNTdHJpbmcgKnVzciA9IG5pbDsKICAgICAgICBOU1N0cmluZyAqaW5wdXQgPSBuaWw7CiAgICAgICAgTlNTdHJpbmcgKmV4cG9ydERpciA9IG5pbDsKICAgICAgICBOU0ludGVnZXIgc2F2ZUV2ZXJ5ID0gMTAwMDsKICAgICAgICBOU0ludGVnZXIgcHJvZ3Jlc3NFdmVyeSA9IDEwMDA7CgogICAgICAgIGludCBvcHQgPSAwOwogICAgICAgIHdoaWxlICgob3B0ID0gZ2V0b3B0X2xvbmcoYXJnYywgYXJndiwgIm06czpkOnU6aTplOng6cDpoIiwgb3B0aW9ucywgTlVMTCkpICE9IC0xKSB7CiAgICAgICAgICAgIHN3aXRjaCAob3B0KSB7CiAgICAgICAgICAgICAgICBjYXNlICdtJzogbW9kZSA9IHN0cmFyZyhvcHRhcmcpOyBicmVhazsKICAgICAgICAgICAgICAgIGNhc2UgJ3MnOiBzdG9yYWdlID0gc3RyYXJnKG9wdGFyZyk7IGJyZWFrOwogICAgICAgICAgICAgICAgY2FzZSAnZCc6IHN5cyA9IHN0cmFyZyhvcHRhcmcpOyBicmVhazsKICAgICAgICAgICAgICAgIGNhc2UgJ3UnOiB1c3IgPSBzdHJhcmcob3B0YXJnKTsgYnJlYWs7CiAgICAgICAgICAgICAgICBjYXNlICdpJzogaW5wdXQgPSBzdHJhcmcob3B0YXJnKTsgYnJlYWs7CiAgICAgICAgICAgICAgICBjYXNlICdlJzogc2F2ZUV2ZXJ5ID0gTUFYKDEsIGF0b2kob3B0YXJnKSk7IGJyZWFrOwogICAgICAgICAgICAgICAgY2FzZSAneCc6IGV4cG9ydERpciA9IHN0cmFyZyhvcHRhcmcpOyBicmVhazsKICAgICAgICAgICAgICAgIGNhc2UgJ3AnOiBwcm9ncmVzc0V2ZXJ5ID0gTUFYKDEsIGF0b2kob3B0YXJnKSk7IGJyZWFrOwogICAgICAgICAgICAgICAgY2FzZSAnaCc6IHVzYWdlKGFyZ3ZbMF0pOyByZXR1cm4gMDsKICAgICAgICAgICAgICAgIGRlZmF1bHQ6IHVzYWdlKGFyZ3ZbMF0pOyByZXR1cm4gMjsKICAgICAgICAgICAgfQogICAgICAgIH0KCiAgICAgICAgaWYgKCFtb2RlIHx8ICFzdG9yYWdlIHx8ICFzeXMgfHwgIXVzciB8fCAhaW5wdXQgfHwgIShbbW9kZSBpc0VxdWFsVG9TdHJpbmc6QCJpbXBvcnQiXSB8fCBbbW9kZSBpc0VxdWFsVG9TdHJpbmc6QCJ2ZXJpZnkiXSkpIHsKICAgICAgICAgICAgdXNhZ2UoYXJndlswXSk7CiAgICAgICAgICAgIHJldHVybiAyOwogICAgICAgIH0KCiAgICAgICAgY29uc3QgY2hhciAqZncgPSAiL0xpYnJhcnkvSW5wdXQgTWV0aG9kcy9Eb3ViYW9JbWUuYXBwL0NvbnRlbnRzL0ZyYW1ld29ya3MvT2ltZUVuZ2luZS5mcmFtZXdvcmsvVmVyc2lvbnMvQS9PaW1lRW5naW5lIjsKICAgICAgICB2b2lkICpoYW5kbGUgPSBkbG9wZW4oZncsIFJUTERfTk9XKTsKICAgICAgICBpZiAoIWhhbmRsZSkgeyBmcHJpbnRmKHN0ZGVyciwgImRsb3BlbiBmYWlsZWQ6ICVzXG4iLCBkbGVycm9yKCkpOyByZXR1cm4gMTsgfQoKICAgICAgICBDbGFzcyBlbmdpbmVDbGFzcyA9IG9iamNfZ2V0Q2xhc3MoIkltZUVuZ2luZSIpOwogICAgICAgIENsYXNzIHBhcmFtc0NsYXNzID0gb2JqY19nZXRDbGFzcygiT2ltZUNvbnZlcnRQYXJhbXMiKTsKICAgICAgICBpZiAoIWVuZ2luZUNsYXNzIHx8ICFwYXJhbXNDbGFzcykgeyBmcHJpbnRmKHN0ZGVyciwgImNsYXNzIG5vdCBmb3VuZFxuIik7IHJldHVybiAxOyB9CgogICAgICAgIGlkIGVuZ2luZSA9IGNhbGwoW2VuZ2luZUNsYXNzIGFsbG9jXSwgQHNlbGVjdG9yKGluaXQpKTsKICAgICAgICBpZiAoIWNvbmZpZ3VyZShlbmdpbmUsIHN0b3JhZ2UsIHN5cywgdXNyKSkgeyBmcHJpbnRmKHN0ZGVyciwgImVuZ2luZSBzZXR1cCBmYWlsZWRcbiIpOyByZXR1cm4gMTsgfQoKICAgICAgICBOU0FycmF5ICpsaW5lcyA9IGxvYWRMaW5lcyhpbnB1dCk7CiAgICAgICAgTlNVSW50ZWdlciB0b3RhbCA9IDA7CiAgICAgICAgTlNVSW50ZWdlciBpbXBvcnRlZCA9IDA7CiAgICAgICAgTlNVSW50ZWdlciBmb3VuZCA9IDA7CiAgICAgICAgTlNVSW50ZWdlciB0b3AxID0gMDsKICAgICAgICBOU1VJbnRlZ2VyIG5vVGVtcGxhdGUgPSAwOwogICAgICAgIE5TVUludGVnZXIgbWFsZm9ybWVkID0gMDsKICAgICAgICBOU1VJbnRlZ2VyIHNldEZhaWxlZCA9IDA7CgogICAgICAgIGZvciAoTlNTdHJpbmcgKmxpbmUgaW4gbGluZXMpIHsKICAgICAgICAgICAgaWYgKGxpbmUubGVuZ3RoID09IDApIHsgY29udGludWU7IH0KICAgICAgICAgICAgTlNBcnJheSAqY29scyA9IFtsaW5lIGNvbXBvbmVudHNTZXBhcmF0ZWRCeVN0cmluZzpAIgkiXTsKICAgICAgICAgICAgaWYgKGNvbHMuY291bnQgPCAyKSB7IG1hbGZvcm1lZCsrOyBjb250aW51ZTsgfQogICAgICAgICAgICBOU1N0cmluZyAqcGlueWluID0gY29sc1swXTsKICAgICAgICAgICAgTlNTdHJpbmcgKndvcmQgPSBjb2xzWzFdOwogICAgICAgICAgICBpZiAocGlueWluLmxlbmd0aCA9PSAwIHx8IHdvcmQubGVuZ3RoID09IDApIHsgbWFsZm9ybWVkKys7IGNvbnRpbnVlOyB9CiAgICAgICAgICAgIHRvdGFsKys7CgogICAgICAgICAgICBAYXV0b3JlbGVhc2Vwb29sIHsKICAgICAgICAgICAgICAgIGlkIHJlc3VsdCA9IGNvbnZlcnQoZW5naW5lLCBwYXJhbXNDbGFzcywgcGlueWluKTsKICAgICAgICAgICAgICAgIE5TQXJyYXkgKmNhbmRpZGF0ZXMgPSBbcmVzdWx0IHZhbHVlRm9yS2V5OkAiY2FuZGlkYXRlcyJdOwoKICAgICAgICAgICAgICAgIGlmIChbbW9kZSBpc0VxdWFsVG9TdHJpbmc6QCJ2ZXJpZnkiXSkgewogICAgICAgICAgICAgICAgICAgIGZvciAoTlNVSW50ZWdlciBpID0gMDsgaSA8IGNhbmRpZGF0ZXMuY291bnQ7IGkrKykgewogICAgICAgICAgICAgICAgICAgICAgICBpZCBjYW5kID0gY2FuZGlkYXRlc1tpXTsKICAgICAgICAgICAgICAgICAgICAgICAgTlNTdHJpbmcgKmNhbmRpZGF0ZVdvcmQgPSBbY2FuZCB2YWx1ZUZvcktleTpAIndvcmRfIl07CiAgICAgICAgICAgICAgICAgICAgICAgIGlmIChbY2FuZGlkYXRlV29yZCBpc0VxdWFsVG9TdHJpbmc6d29yZF0pIHsKICAgICAgICAgICAgICAgICAgICAgICAgICAgIGZvdW5kKys7CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiAoaSA9PSAwKSB7IHRvcDErKzsgfQogICAgICAgICAgICAgICAgICAgICAgICAgICAgYnJlYWs7CiAgICAgICAgICAgICAgICAgICAgICAgIH0KICAgICAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgICAgICAgICAgY29udGludWU7CiAgICAgICAgICAgICAgICB9CgogICAgICAgICAgICAgICAgaWYgKGNhbmRpZGF0ZXMuY291bnQgPT0gMCkgeyBub1RlbXBsYXRlKys7IGNvbnRpbnVlOyB9CiAgICAgICAgICAgICAgICBpZCBjYW5kID0gY2FuZGlkYXRlc1swXTsKICAgICAgICAgICAgICAgIEB0cnkgewogICAgICAgICAgICAgICAgICAgIFtjYW5kIHNldFZhbHVlOndvcmQgZm9yS2V5OkAid29yZF8iXTsKICAgICAgICAgICAgICAgICAgICBbY2FuZCBzZXRWYWx1ZTp3b3JkIGZvcktleTpAImRpc3BsYXlTdHJpbmdfIl07CiAgICAgICAgICAgICAgICAgICAgW2NhbmQgc2V0VmFsdWU6d29yZCBmb3JLZXk6QCJjb21taXRXb3JkXyJdOwogICAgICAgICAgICAgICAgICAgIFtjYW5kIHNldFZhbHVlOndvcmQgZm9yS2V5OkAicmF3V29yZF8iXTsKICAgICAgICAgICAgICAgIH0gQGNhdGNoIChOU0V4Y2VwdGlvbiAqZSkgewogICAgICAgICAgICAgICAgICAgIHNldEZhaWxlZCsrOwogICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlOwogICAgICAgICAgICAgICAgfQogICAgICAgICAgICAgICAgY2FsbE9iajIoZW5naW5lLCBAc2VsZWN0b3IobGVhcm5DYW5kaWRhdGVQaW55aW46V29yZDopLCBwaW55aW4sIGNhbmQpOwogICAgICAgICAgICAgICAgaW1wb3J0ZWQrKzsKICAgICAgICAgICAgICAgIGlmIChpbXBvcnRlZCAlIHNhdmVFdmVyeSA9PSAwKSB7CiAgICAgICAgICAgICAgICAgICAgY2FsbEJvb2xCb29sKGVuZ2luZSwgQHNlbGVjdG9yKHNhdmVVc3JEaWN0OiksIFlFUyk7CiAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgIH0KCiAgICAgICAgICAgIGlmICh0b3RhbCAlIHByb2dyZXNzRXZlcnkgPT0gMCkgewogICAgICAgICAgICAgICAgZnByaW50ZihzdGRlcnIsICJwcm9ncmVzcyBtb2RlPSVzIHRvdGFsPSVsdSBpbXBvcnRlZD0lbHUgZm91bmQ9JWx1IHRvcDE9JWx1IG5vX3RlbXBsYXRlPSVsdSBtYWxmb3JtZWQ9JWx1IHNldF9mYWlsZWQ9JWx1XG4iLAogICAgICAgICAgICAgICAgICAgICAgICBbbW9kZSBVVEY4U3RyaW5nXSwgKHVuc2lnbmVkIGxvbmcpdG90YWwsICh1bnNpZ25lZCBsb25nKWltcG9ydGVkLCAodW5zaWduZWQgbG9uZylmb3VuZCwKICAgICAgICAgICAgICAgICAgICAgICAgKHVuc2lnbmVkIGxvbmcpdG9wMSwgKHVuc2lnbmVkIGxvbmcpbm9UZW1wbGF0ZSwgKHVuc2lnbmVkIGxvbmcpbWFsZm9ybWVkLCAodW5zaWduZWQgbG9uZylzZXRGYWlsZWQpOwogICAgICAgICAgICB9CiAgICAgICAgfQoKICAgICAgICBCT09MIHNhdmVkID0gWUVTOwogICAgICAgIGlmIChbbW9kZSBpc0VxdWFsVG9TdHJpbmc6QCJpbXBvcnQiXSkgeyBzYXZlZCA9IGNhbGxCb29sQm9vbChlbmdpbmUsIEBzZWxlY3RvcihzYXZlVXNyRGljdDopLCBZRVMpOyB9CiAgICAgICAgaWYgKGV4cG9ydERpcikgewogICAgICAgICAgICBbW05TRmlsZU1hbmFnZXIgZGVmYXVsdE1hbmFnZXJdIGNyZWF0ZURpcmVjdG9yeUF0UGF0aDpleHBvcnREaXIgd2l0aEludGVybWVkaWF0ZURpcmVjdG9yaWVzOllFUyBhdHRyaWJ1dGVzOm5pbCBlcnJvcjpuaWxdOwogICAgICAgICAgICAoKHZvaWQgKCopKGlkLCBTRUwsIGlkKSlvYmpjX21zZ1NlbmQpKGVuZ2luZSwgQHNlbGVjdG9yKGV4cG9ydFVzZXJEaWN0OiksIGV4cG9ydERpcik7CiAgICAgICAgfQoKICAgICAgICBwcmludGYoIlNVTU1BUlkJbW9kZT0lcwl0b3RhbD0lbHUJaW1wb3J0ZWQ9JWx1CWZvdW5kPSVsdQl0b3AxPSVsdQlub190ZW1wbGF0ZT0lbHUJbWFsZm9ybWVkPSVsdQlzZXRfZmFpbGVkPSVsdQlzYXZlZD0lZFxuIiwKICAgICAgICAgICAgICAgW21vZGUgVVRGOFN0cmluZ10sICh1bnNpZ25lZCBsb25nKXRvdGFsLCAodW5zaWduZWQgbG9uZylpbXBvcnRlZCwgKHVuc2lnbmVkIGxvbmcpZm91bmQsICh1bnNpZ25lZCBsb25nKXRvcDEsCiAgICAgICAgICAgICAgICh1bnNpZ25lZCBsb25nKW5vVGVtcGxhdGUsICh1bnNpZ25lZCBsb25nKW1hbGZvcm1lZCwgKHVuc2lnbmVkIGxvbmcpc2V0RmFpbGVkLCBzYXZlZCk7CgogICAgICAgIGRsY2xvc2UoaGFuZGxlKTsKICAgIH0KICAgIHJldHVybiAwOwp9Cg==
"""

BUILTIN_NAMES = []

PINYIN_OVERRIDES = {}


@dataclass(frozen=True)
class Entry:
    pinyin: str
    word: str
    source: str
    freq: int = 0


def parse_sgpu(path: Path):
    data = path.read_bytes()
    if data[:4] != b"SGPU":
        raise ValueError(f"not an SGPU file: {path}")
    _index_offset, _index_size, count, dict_offset, _dict_size, dict_used = struct.unpack_from("<6I", data, 0x38)
    offsets = sorted({
        struct.unpack_from("<I", data, _index_offset + i * 4)[0]
        for i in range(count)
    })
    offsets = [offset for offset in offsets if 0 <= offset < dict_used]
    offsets.append(dict_used)

    for start, end in zip(offsets, offsets[1:]):
        record = data[dict_offset + start:dict_offset + end]
        if len(record) < 17:
            continue
        try:
            freq = struct.unpack_from("<H", record, 0)[0]
            py_bytes = struct.unpack_from("<H", record, 9)[0]
            if py_bytes <= 0 or py_bytes % 2 or py_bytes > 128:
                continue
            pos = 11 + py_bytes
            if pos + 4 > len(record):
                continue
            value_bytes = struct.unpack_from("<H", record, pos)[0]
            pos += 2
            word_bytes = struct.unpack_from("<H", record, pos)[0]
            pos += 2
            if word_bytes <= 0 or word_bytes > 256 or word_bytes % 2 or value_bytes != py_bytes + word_bytes + 4:
                continue
            if pos + word_bytes + 2 > len(record):
                continue
            word = record[pos:pos + word_bytes].decode("utf-16le")
            pos += word_bytes
            dup_py_bytes = struct.unpack_from("<H", record, pos)[0]
            if dup_py_bytes != py_bytes:
                continue
            pinyin = pinyin_for_word(word)
            if not pinyin:
                continue
        except Exception:
            continue
        yield Entry(pinyin, word, "sogou", freq)


def clean_entry(entry: Entry) -> Entry | None:
    word = entry.word.strip()
    pinyin = entry.pinyin.strip().lower().replace(" ", "'")
    if not word or not pinyin or "\t" in word or "\n" in word or "\r" in word:
        return None
    if len(word.splitlines()) != 1 or len(pinyin.splitlines()) != 1:
        return None
    if any(unicodedata.category(ch)[0] == "C" for ch in word):
        return None
    if len(word) > 64 or len(pinyin) > 160:
        return None
    if not re.fullmatch(r"[a-z']+", pinyin):
        return None
    return Entry(pinyin, word, entry.source, entry.freq)


def pinyin_for_word(word: str) -> str | None:
    try:
        from pypinyin import Style, lazy_pinyin
    except Exception as exc:
        raise RuntimeError("pypinyin is required to derive pinyin from Sogou backup words") from exc
    syllables = lazy_pinyin(word, style=Style.NORMAL, strict=False, errors="default")
    normalized = []
    for syllable in syllables:
        value = syllable.strip().lower()
        if not value:
            continue
        if re.fullmatch(r"[a-z]+", value):
            normalized.append(value)
        else:
            return None
    return "'".join(normalized) if normalized else None


def pinyin_for_name(name: str) -> str:
    if name in PINYIN_OVERRIDES:
        return PINYIN_OVERRIDES[name]
    if re.fullmatch(r"[A-Za-z][A-Za-z ._-]*", name):
        return re.sub(r"[^A-Za-z]+", "'", name).strip("'").lower()
    from pypinyin import Style, lazy_pinyin
    return "'".join(lazy_pinyin(name, style=Style.NORMAL, strict=False, errors="ignore"))


def load_names(paths: list[Path], explicit: list[str]) -> list[str]:
    names = [*BUILTIN_NAMES, *explicit]
    for path in paths:
        names.extend(line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    result, seen = [], set()
    for name in names:
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result


def resolve_user_dir(value: str | None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    dirs = [p for p in DEFAULT_ACCOUNT_ROOT.iterdir() if p.is_dir()]
    if len(dirs) != 1:
        raise RuntimeError(f"expected one Doubao account dir under {DEFAULT_ACCOUNT_ROOT}, got {len(dirs)}; pass --user-dict-dir")
    return dirs[0]


def resolve_wetype_db(value: Path) -> Path:
    candidate = value.expanduser().resolve()
    if (candidate / "CURRENT").is_file():
        return candidate
    config = candidate / "db_path.conf"
    if config.is_file():
        child_name = config.read_text(encoding="utf-8").strip()
        if not child_name or Path(child_name).name != child_name:
            raise RuntimeError(f"invalid WeType db_path.conf: {config}")
        child = candidate / child_name
        if (child / "CURRENT").is_file():
            return child
        raise RuntimeError(f"WeType database from {config} is missing CURRENT: {child}")
    children = sorted(p for p in candidate.iterdir() if p.is_dir() and (p / "CURRENT").is_file())
    if len(children) == 1:
        return children[0]
    raise RuntimeError(
        f"expected one WeType LevelDB under {candidate}, got {len(children)}; "
        "pass --wetype-user-dict PATH"
    )


def run(cmd: list[str], *, env=None, stdout_path: Path | None = None):
    if stdout_path:
        with stdout_path.open("w", encoding="utf-8") as out:
            subprocess.run(cmd, check=True, text=True, stdout=out, stderr=subprocess.STDOUT, env=env)
    else:
        subprocess.run(cmd, check=True, text=True, env=env)


def write_tsv(path: Path, entries: list[Entry]) -> None:
    path.write_text("".join(f"{e.pinyin}\t{e.word}\t{e.source}\n" for e in entries), encoding="utf-8")
    path.chmod(0o600)


def compile_helper(run_dir: Path) -> Path:
    source = run_dir / "embedded_bulk_user_word_tool.m"
    binary = run_dir / "embedded_bulk_user_word_tool"
    source.write_bytes(base64.b64decode(EMBEDDED_HELPER_SOURCE_B64))
    source.chmod(0o600)
    run(["clang", "-fobjc-arc", "-framework", "Foundation", "-o", str(binary), str(source)])
    binary.chmod(0o700)
    return binary


def process_running(name: str) -> bool:
    return subprocess.run(
        ["pgrep", "-x", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode == 0


def stop_process(name: str) -> None:
    subprocess.run(["pkill", "-x", name], check=False)
    for _ in range(40):
        if not process_running(name):
            return
        time.sleep(0.25)
    raise RuntimeError(f"{name} is still running after pkill")


def stop_doubao() -> None:
    stop_process("DoubaoIme")


def snapshot_wetype_db(source: Path, destination: Path, *, stop_wetype: bool) -> None:
    was_running = process_running("WeType")
    stopped = False
    try:
        if stop_wetype and was_running:
            stop_process("WeType")
            stopped = True
        shutil.copytree(source, destination)
    finally:
        if stopped:
            subprocess.run(["open", "-a", str(WETYPE_APP)], check=False)


def latest_child(path: Path) -> Path | None:
    if not path.exists():
        return None
    dirs = [p for p in path.iterdir() if p.is_dir()]
    return max(dirs, key=lambda p: p.stat().st_mtime) if dirs else None


def parse_usr_export_count(export_root: Path):
    latest = latest_child(export_root)
    if not latest:
        return None, None
    text_path = latest / "usr.dat.export.txt"
    if not text_path.exists():
        return None, None
    text = text_path.read_text(encoding="utf-8", errors="replace")
    used = re.search(r"已使用索引数量\s*:\s*(\d+)", text)
    total = re.search(r"索引总数量\s*:\s*(\d+)", text)
    return (int(used.group(1)) if used else None, int(total.group(1)) if total else None)


def ensure_runtime_requirements(*, will_write: bool, need_pypinyin: bool) -> None:
    if need_pypinyin:
        try:
            import pypinyin  # noqa: F401
        except Exception as exc:
            raise RuntimeError("missing Python package: pypinyin; install it with: python3 -m pip install pypinyin") from exc
    if will_write and shutil.which("clang") is None:
        raise RuntimeError("missing clang; install Xcode Command Line Tools with: xcode-select --install")
    if will_write and not DEFAULT_FRAMEWORKS.exists():
        raise RuntimeError(f"Doubao IME frameworks not found: {DEFAULT_FRAMEWORKS}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Import Sogou or WeType user words into Doubao IME.")
    ap.add_argument(
        "backup_path",
        nargs="?",
        type=Path,
        metavar="SOGOU_BACKUP",
        help="Path to a Sogou .bin/.sgpu backup. Alternative to --wetype-user-dict and --names-only.",
    )
    ap.add_argument(
        "--sogou-backup",
        type=Path,
        help="Path to the Sogou input method backup .bin/.sgpu file. Same as positional SOGOU_BACKUP.",
    )
    ap.add_argument(
        "--wetype-user-dict",
        "--wechat-input-method",
        nargs="?",
        const=DEFAULT_WETYPE_ROOT,
        type=Path,
        metavar="PATH",
        help="Import the WeType (微信输入法) user dictionary. PATH may be its v5 root or LevelDB directory.",
    )
    ap.add_argument("--user-dict-dir")
    ap.add_argument("--sys-dict-dir", type=Path, default=DEFAULT_SYS_DICT)
    ap.add_argument("--work-dir", type=Path, default=BASE_DIR)
    ap.add_argument("--limit", type=int, default=0, help="Limit source entries for testing; 0 means all.")
    ap.add_argument("--name", action="append", default=[])
    ap.add_argument("--names-file", action="append", type=Path, default=[])
    ap.add_argument("--names-only", action="store_true", help="Only import built-in/explicit names; do not parse a Sogou backup.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-stop", action="store_true")
    ap.add_argument(
        "--no-stop-wetype",
        action="store_true",
        help="Copy WeType while it is running (less consistent; intended only for diagnostics).",
    )
    ap.add_argument("--skip-backup", action="store_true")
    ap.add_argument("--save-every", type=int, default=1000)
    ap.add_argument("--progress-every", type=int, default=1000)
    ap.add_argument("--verify-source-samples", "--verify-sogou-samples", dest="verify_source_samples", type=int, default=50)
    args = ap.parse_args()

    if args.backup_path and args.sogou_backup and args.backup_path.expanduser() != args.sogou_backup.expanduser():
        ap.error("pass the Sogou backup either positionally or with --sogou-backup, not both")
    sogou_arg = args.sogou_backup or args.backup_path
    wetype_arg = args.wetype_user_dict
    if sogou_arg and wetype_arg:
        ap.error("choose exactly one dictionary source: Sogou or WeType")
    if args.names_only and (sogou_arg or wetype_arg):
        ap.error("--names-only cannot be combined with a dictionary source")
    if not args.names_only and not (sogou_arg or wetype_arg):
        ap.error("provide SOGOU_BACKUP, --wetype-user-dict, or --names-only")
    sogou_path = sogou_arg.expanduser().resolve() if sogou_arg else None
    wetype_path = resolve_wetype_db(wetype_arg) if wetype_arg else None
    user_dir = resolve_user_dir(args.user_dict_dir)
    sys_dir = args.sys_dict_dir.expanduser().resolve()
    if sogou_path and not sogou_path.exists():
        raise FileNotFoundError(sogou_path)
    if not user_dir.exists():
        raise FileNotFoundError(user_dir)
    if not sys_dir.exists():
        raise FileNotFoundError(sys_dir)
    ensure_runtime_requirements(
        will_write=not args.dry_run,
        need_pypinyin=bool(sogou_path or args.name or args.names_file or BUILTIN_NAMES),
    )

    timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    run_dir = args.work_dir.expanduser().resolve() / f"doubao-user-dict-import-{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    run_dir.chmod(0o700)
    storage_dir = run_dir / "storage"
    export_dir = run_dir / "export"
    storage_dir.mkdir()

    seen, source_entries, skipped = set(), [], 0
    wetype_stats: ScanStats | None = None
    if sogou_path:
        for entry in parse_sgpu(sogou_path):
            cleaned = clean_entry(entry)
            if cleaned is None:
                skipped += 1
                continue
            key = (cleaned.pinyin, cleaned.word)
            if key in seen:
                continue
            seen.add(key)
            source_entries.append(cleaned)
    elif wetype_path:
        snapshot_dir = run_dir / "wetype-leveldb-snapshot"
        snapshot_wetype_db(wetype_path, snapshot_dir, stop_wetype=not args.no_stop_wetype)
        wetype_words, wetype_stats = scan_wetype_leveldb(snapshot_dir)
        for item in wetype_words:
            cleaned = clean_entry(Entry(item.pinyin, item.word, "wetype", item.sequence))
            if cleaned is None:
                skipped += 1
                continue
            key = (cleaned.pinyin, cleaned.word)
            if key in seen:
                continue
            seen.add(key)
            source_entries.append(cleaned)
    parsed_unique = len(source_entries)
    source_entries.sort(key=lambda e: (e.freq, e.pinyin, e.word))
    if args.limit > 0:
        source_entries = source_entries[-args.limit:]

    name_entries = [clean_entry(Entry(pinyin_for_name(name), name, "name", 999999)) for name in load_names(args.names_file, args.name)]
    name_entries = [entry for entry in name_entries if entry is not None]
    entries = source_entries + name_entries
    verify_entries = source_entries[-max(0, args.verify_source_samples):] + name_entries
    import_tsv = run_dir / "import.tsv"
    verify_tsv = run_dir / "verify.tsv"
    write_tsv(import_tsv, entries)
    write_tsv(verify_tsv, verify_entries)

    print(f"run_dir={run_dir}")
    print(f"source={'wetype' if wetype_path else 'sogou' if sogou_path else 'names'}")
    print(f"sogou_backup={sogou_path if sogou_path else 'none'}")
    print(f"wetype_user_dict={wetype_path if wetype_path else 'none'}")
    print(f"names_only={str(args.names_only).lower()}")
    print(f"source_parsed_unique={parsed_unique}")
    print(f"source_selected={len(source_entries)}")
    print(f"source_skipped_invalid={skipped}")
    if wetype_stats:
        print(f"wetype_table_files={wetype_stats.table_files}")
        print(f"wetype_log_files={wetype_stats.log_files}")
        print(f"wetype_leveldb_records={wetype_stats.physical_records}")
        print(f"wetype_live_pair_keys={wetype_stats.live_pair_keys}")
        print(f"wetype_deleted_pair_keys={wetype_stats.deleted_pair_keys}")
        print(f"wetype_malformed_pair_keys={wetype_stats.malformed_pair_keys}")
    print(f"name_selected={len(name_entries)}")
    print(f"import_total={len(entries)}")
    print(f"user_dict_dir={user_dir}")
    if args.dry_run:
        print("dry_run=true")
        return 0

    helper = compile_helper(run_dir)
    env = os.environ.copy()
    env["DYLD_LIBRARY_PATH"] = str(DEFAULT_FRAMEWORKS)
    env["DYLD_FRAMEWORK_PATH"] = str(DEFAULT_FRAMEWORKS)
    if not args.skip_backup:
        backup_dir = run_dir / "backup-before-import"
        run(["ditto", str(user_dir), str(backup_dir)])
        print(f"backup_dir={backup_dir}")
    if not args.no_stop:
        stop_doubao()

    import_log = run_dir / "import.log"
    try:
        run([str(helper), "--mode", "import", "--storage", str(storage_dir), "--sys-dict", str(sys_dir), "--user-dict", str(user_dir), "--input", str(import_tsv), "--save-every", str(args.save_every), "--progress-every", str(args.progress_every), "--export-dir", str(export_dir)], env=env, stdout_path=import_log)
    finally:
        if not args.no_stop:
            subprocess.run(["open", "-a", "/Library/Input Methods/DoubaoIme.app"], check=False)

    verify_storage_dir = run_dir / "verify-storage"
    verify_storage_dir.mkdir()
    verify_log = run_dir / "verify.log"
    run([str(helper), "--mode", "verify", "--storage", str(verify_storage_dir), "--sys-dict", str(sys_dir), "--user-dict", str(user_dir), "--input", str(verify_tsv), "--progress-every", str(args.progress_every)], env=env, stdout_path=verify_log)
    used, total = parse_usr_export_count(export_dir)
    print(f"import_log={import_log}")
    print(f"verify_log={verify_log}")
    print(f"usr_index_used={used}")
    print(f"usr_index_total={total}")
    print(import_log.read_text(encoding="utf-8", errors="replace").splitlines()[-1])
    print(verify_log.read_text(encoding="utf-8", errors="replace").splitlines()[-1])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
