import lxml.etree as ET

def parse(xml_bytes):
    parser = ET.XMLParser(resolve_entities=True, no_network=False)
    return ET.fromstring(xml_bytes, parser)
