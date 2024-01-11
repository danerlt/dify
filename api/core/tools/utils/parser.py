
from core.tools.entities.tool_bundle import ApiBasedToolBundle
from core.tools.entities.tool_entities import ToolParamter, ToolParamterOption
from core.tools.entities.common_entities import I18nObject
from core.tools.errors import ToolProviderNotFoundError, ToolNotSupportedError

from typing import List

from yaml import FullLoader, load
from json import loads as json_loads, dumps as json_dumps
from requests import get

class ApiBasedToolSchemaParser:
    @staticmethod
    def parse_openapi_to_tool_bundle(openapi: dict, warning: dict = None) -> List[ApiBasedToolBundle]:
        warning = warning if warning is not None else {}

        if len(openapi['servers']) == 0:
            raise ToolProviderNotFoundError('No server found in the openapi yaml.')

        server_url = openapi['servers'][0]['url']

        # list all interfaces
        interfaces = []
        for path, path_item in openapi['paths'].items():
            methods = ['get', 'post', 'put', 'delete', 'patch', 'head', 'options', 'trace']
            for method in methods:
                if method in path_item:
                    interfaces.append({
                        'path': path,
                        'method': method,
                        'operation': path_item[method],
                    })

        # get all parameters
        bundles = []
        for interface in interfaces:
            # convert parameters
            parameters = []
            if 'parameters' in interface['operation']:
                for parameter in interface['operation']['parameters']:
                    parameters.append(ToolParamter(
                        name=parameter['name'],
                        label=I18nObject(
                            en_US=parameter['name'],
                            zh_Hans=parameter['name']
                        ),
                        human_description=I18nObject(
                            en_US=parameter['description'],
                            zh_Hans=parameter['description']
                        ),
                        type=ToolParamter.ToolParameterType.STRING,
                        required=parameter['required'],
                        form=ToolParamter.ToolParameterForm.LLM,
                        llm_description=parameter['description'],
                        default=parameter['default'] if 'default' in parameter else None,
                    ))
            # create tool bundle
            # check if there is a request body
            if 'requestBody' in interface['operation']:
                request_body = interface['operation']['requestBody']
                if 'content' in request_body:
                    for content_type, content in request_body['content'].items():
                        # if there is a reference, get the reference and overwrite the content
                        if 'schema' not in content:
                            content

                        if '$ref' in content['schema']:
                            # get the reference
                            root = openapi
                            reference = content['schema']['$ref'].split('/')[1:]
                            for ref in reference:
                                root = root[ref]
                            # overwrite the content
                            interface['operation']['requestBody']['content'][content_type]['schema'] = root
                    # parse body parameters
                    if 'schema' in interface['operation']['requestBody']['content'][content_type]:
                        body_schema = interface['operation']['requestBody']['content'][content_type]['schema']
                        required = body_schema['required'] if 'required' in body_schema else []
                        properties = body_schema['properties'] if 'properties' in body_schema else {}
                        for name, property in properties.items():
                            parameters.append(ToolParamter(
                                name=name,
                                label=I18nObject(
                                    en_US=name,
                                    zh_Hans=name
                                ),
                                human_description=I18nObject(
                                    en_US=property['description'] if 'description' in property else '',
                                    zh_Hans=property['description'] if 'description' in property else ''
                                ),
                                type=ToolParamter.ToolParameterType.STRING,
                                required=name in required,
                                form=ToolParamter.ToolParameterForm.LLM,
                                llm_description=property['description'] if 'description' in property else '',
                                default=property['default'] if 'default' in property else None,
                            ))

            # check if parameters is duplicated
            parameters_count = {}
            for parameter in parameters:
                if parameter.name not in parameters_count:
                    parameters_count[parameter.name] = 0
                parameters_count[parameter.name] += 1
            for name, count in parameters_count.items():
                if count > 1:
                    warning['duplicated_parameter'] = f'Parameter {name} is duplicated.'

            bundles.append(ApiBasedToolBundle(
                server_url=server_url + interface['path'],
                method=interface['method'],
                summary=interface['operation']['summary'] if 'summary' in interface['operation'] else None,
                operation_id=interface['operation']['operationId'],
                parameters=parameters,
                author='',
                icon=None,
                openapi=interface['operation'],
            ))

        return bundles
        
    @staticmethod
    def parse_openapi_yaml_to_tool_bundle(yaml: str, warning: dict = None) -> List[ApiBasedToolBundle]:
        """
            parse openapi yaml to tool bundle

            :param yaml: the yaml string
            :return: the tool bundle
        """
        warning = warning if warning is not None else {}

        openapi: dict = load(yaml, Loader=FullLoader)
        if openapi is None:
            raise ToolProviderNotFoundError('Invalid openapi yaml.')
        return ApiBasedToolSchemaParser.parse_openapi_to_tool_bundle(openapi, warning=warning)
    
    @staticmethod
    def parse_openai_plugin_json_to_tool_bundle(json: str, warning: dict = None) -> List[ApiBasedToolBundle]:
        """
            parse openapi plugin yaml to tool bundle

            :param json: the json string
            :return: the tool bundle
        """
        warning = warning if warning is not None else {}

        try:
            openai_plugin = json_loads(json)
            api = openai_plugin['api']
            api_url = api['url']
            api_type = api['type']
        except:
            raise ToolProviderNotFoundError('Invalid openai plugin json.')
        
        if api_type != 'openapi':
            raise ToolNotSupportedError('Only openapi is supported now.')
        
        # get openapi yaml
        response = get(api_url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        }, timeout=5)

        if response.status_code != 200:
            raise ToolProviderNotFoundError('cannot get openapi yaml from url.')
        
        return ApiBasedToolSchemaParser.parse_openapi_yaml_to_tool_bundle(response.text, warning=warning)