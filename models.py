from dataclasses import dataclass


@dataclass
class UrlData:
    id: str
    h1: str
    h2: str
    h3: str
    h4: str
    h5: str
    paragraf_content: str
    url: str


@dataclass
class RegistrationClientId:
    message: str
    client_id: str


@dataclass
class WebhookUrlRegistration:
    message: str
    webhook_url: str
