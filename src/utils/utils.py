import xmltodict
import xml.etree.ElementTree as ET
from xmltoxsd import XSDGenerator




import re
import xmltodict
from io import BytesIO
import xml.etree.ElementTree as ET

def validate_tag_name(name):
    """
    Проверяет и исправляет имя тега, чтобы оно было валидным XML именем
    """
    # XML имена не могут начинаться с цифры
    if name and name[0].isdigit():
        name = "n" + name
    
    # Заменяем недопустимые символы на подчеркивание
    name = re.sub(r'[^a-zA-Z0-9\-_.]', '_', name)
    
    # Имя не может быть пустым
    if not name:
        name = "item"
    
    return name

def escape_xml(text):
    """Экранирует специальные XML символы"""
    if text is None:
        return ""
    text = str(text)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text

def dict_to_xml(d, level=0):
    """
    Преобразование словаря в XML с валидацией имен тегов
    """
    indent = "  " * level
    result = []
    
    if isinstance(d, dict):
        for key, value in d.items():
            # Валидируем имя тега
            safe_key = validate_tag_name(str(key))
            
            if isinstance(value, dict):
                result.append(f"{indent}<{safe_key}>")
                result.append(dict_to_xml(value, level + 1))
                result.append(f"{indent}</{safe_key}>")
            elif isinstance(value, list):
                result.append(f"{indent}<{safe_key}>")
                for item in value:
                    if isinstance(item, dict):
                        result.append(dict_to_xml(item, level + 1))
                    else:
                        result.append(f"{indent}  <item>{escape_xml(str(item))}</item>")
                result.append(f"{indent}</{safe_key}>")
            else:
                result.append(f"{indent}<{safe_key}>{escape_xml(str(value))}</{safe_key}>")
    elif isinstance(d, list):
        for item in d:
            if isinstance(item, dict):
                result.append(dict_to_xml(item, level))
            else:
                result.append(f"{indent}<item>{escape_xml(str(item))}</item>")
    else:
        result.append(f"{indent}<value>{escape_xml(str(d))}</value>")
    
    return "\n".join(result)

def collect_xml_response(input_data):
    """
    Основная функция для сбора XML ответа из различных структур данных
    Поддерживает словари, списки, вложенные структуры
    """
    # Обработка входных данных
    if isinstance(input_data, list):
        xml_parts = []
        for item in input_data:
            if isinstance(item, list):
                for subitem in item:
                    if isinstance(subitem, dict):
                        xml_parts.append(dict_to_xml(subitem, 1))
                    else:
                        xml_parts.append(f"  <item>{escape_xml(str(subitem))}</item>")
            elif isinstance(item, dict):
                xml_parts.append(dict_to_xml(item, 1))
            else:
                xml_parts.append(f"  <value>{escape_xml(str(item))}</value>")
        
        return f"<root>\n" + "\n".join(xml_parts) + "\n</root>"
    
    elif isinstance(input_data, dict):
        return f"<root>\n{dict_to_xml(input_data, 1)}\n</root>"
    
    else:
        return f"<root>\n  <value>{escape_xml(str(input_data))}</value>\n</root>"

def validate_xml(xml_string):
    """
    Проверяет XML на валидность
    """
    try:
        ET.fromstring(xml_string)
        return True, "XML валидный"
    except ET.ParseError as e:
        return False, str(e)

def fix_xml_issues(xml_string):
    """
    Исправляет распространенные проблемы в XML
    """
    def fix_tag_name(match):
        tag = match.group(1)
        fixed_tag = validate_tag_name(tag)
        return f"<{fixed_tag}" if match.group(0).startswith('<') else f"</{fixed_tag}>"
    
    xml_string = re.sub(r'<([^>\s/]+)', fix_tag_name, xml_string)
    xml_string = re.sub(r'</([^>\s/]+)', fix_tag_name, xml_string)
    
    return xml_string

def convertdicttoXSD(input_data, output_file:str = None):
    """
    Конвертирует словарь или список в XSD схему
    """
    # Создаем экземпляр генератора
    generator = XSDGenerator()
    
    # Конвертируем в XML
    xml_string = collect_xml_response(input_data)
    
    # Удаляем XML декларацию если есть
    xml_string = re.sub(r'<\?xml[^>]+\?>', '', xml_string).strip()
    
    # Проверяем XML на валидность
    is_valid, error_msg = validate_xml(xml_string)
    if not is_valid:
        xml_string = fix_xml_issues(xml_string)
    
    
    # Конвертируем в байты
    xml_bytes = xml_string.encode('utf-8')
    xml_file = BytesIO(xml_bytes)
    
    try:
        # Генерируем XSD
        xsd_schema_string = generator.generate_xsd(xml_file, min_occurs="0")
        
        
        if output_file:
            with open(output_file, "w", encoding='utf-8') as f:
                f.write(xsd_schema_string)        
        return xsd_schema_string
        
    except Exception as e:
        print(f"Failed to generate XSD schema: {e}")
        print("XML that caused the error:")
        print(xml_string)
        raise