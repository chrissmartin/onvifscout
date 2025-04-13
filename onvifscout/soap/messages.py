import uuid

from .namespaces import SOAP_NAMESPACES


class SOAPMessageBuilder:
    @staticmethod
    def create_envelope(body_content: str) -> str:
        """Create a SOAP envelope with the given body content"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="{SOAP_NAMESPACES["s"]}">
    <s:Body>
        {body_content}
    </s:Body>
</s:Envelope>"""

    @staticmethod
    def create_discovery_probe() -> str:
        """Create WS-Discovery probe message"""
        message_uuid = uuid.uuid4()
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope
    xmlns:s="{SOAP_NAMESPACES["s"]}"
    xmlns:a="{SOAP_NAMESPACES["a"]}"
    xmlns:d="{SOAP_NAMESPACES["d"]}"
    xmlns:dn="{SOAP_NAMESPACES["dn"]}">
    <s:Header>
        <a:Action s:mustUnderstand="1">http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</a:Action>
        <a:MessageID>urn:uuid:{message_uuid}</a:MessageID>
        <a:To s:mustUnderstand="1">urn:schemas-xmlsoap-org:ws:2005:04:discovery</a:To>
    </s:Header>
    <s:Body>
        <d:Probe>
            <d:Types>dn:NetworkVideoTransmitter tds:Device</d:Types>
        </d:Probe>
    </s:Body>
</s:Envelope>"""

    @staticmethod
    def create_get_device_info() -> str:
        """Create GetDeviceInformation request"""
        return SOAPMessageBuilder.create_envelope(
            '<GetDeviceInformation xmlns="http://www.onvif.org/ver10/device/wsdl"/>'
        )

    @staticmethod
    def create_get_capabilities() -> str:
        """Create GetCapabilities request"""
        return SOAPMessageBuilder.create_envelope(
            """<tds:GetCapabilities xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
                <tds:Category>All</tds:Category>
            </tds:GetCapabilities>"""
        )

    @staticmethod
    def create_get_services() -> str:
        """Create GetServices request"""
        return SOAPMessageBuilder.create_envelope(
            """<tds:GetServices xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
                <tds:IncludeCapability>true</tds:IncludeCapability>
            </tds:GetServices>"""
        )

    @staticmethod
    def create_get_profiles() -> str:
        """Create GetProfiles request"""
        return SOAPMessageBuilder.create_envelope(
            '<GetProfiles xmlns="http://www.onvif.org/ver10/media/wsdl"/>'
        )

    @staticmethod
    def create_get_snapshot_uri(profile_token: str) -> str:
        """Create GetSnapshotUri request"""
        return SOAPMessageBuilder.create_envelope(
            f"""<GetSnapshotUri xmlns="http://www.onvif.org/ver10/media/wsdl">
                <ProfileToken>{profile_token}</ProfileToken>
            </GetSnapshotUri>"""
        )
