"""Factory functions for Azure clients."""
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient


def get_openai_client(config: dict) -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=config["azure_openai_endpoint"],
        api_key=config["azure_openai_api_key"],
        api_version=config["azure_openai_api_version"],
    )


def get_search_client(config: dict, index_name: str) -> SearchClient:
    return SearchClient(
        endpoint=config["search_endpoint"],
        index_name=index_name,
        credential=AzureKeyCredential(config["search_api_key"]),
    )


def get_search_index_client(config: dict) -> SearchIndexClient:
    return SearchIndexClient(
        endpoint=config["search_endpoint"],
        credential=AzureKeyCredential(config["search_api_key"]),
    )
