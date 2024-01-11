from core.tools.provider.builtin_tool import BuiltinTool
from core.tools.entities.tool_entities import ToolInvokeMessage
from core.model_runtime.entities.message_entities import PromptMessage

from pydantic import BaseModel, Field

from typing import Any, Dict, List, Union, Optional, Tuple

from langchain import WikipediaAPIWrapper
from langchain.tools import WikipediaQueryRun

class WikipediaInput(BaseModel):
    query: str = Field(..., description="search query.")

class WikiPediaSearchTool(BuiltinTool):
    def _invoke(self, 
                user_id: str, 
               tool_paramters: Dict[str, Any], 
        ) -> Union[ToolInvokeMessage, List[ToolInvokeMessage]]:
        """
            invoke tools
        """
        query = tool_paramters.get('query', '')
        if not query:
            return self.create_text_message('Please input query')
        
        tool = WikipediaQueryRun(
            name="wikipedia",
            api_wrapper=WikipediaAPIWrapper(doc_content_chars_max=4000),
            args_schema=WikipediaInput
        )

        result = tool.run(tool_input={
            'query': query
        })

        return self.create_text_message(result)
    
    def validate_credentials(self, credentails: Dict[str, Any], parameters: Dict[str, Any]) -> None:
        pass