from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS
from ddgs.exceptions import DDGSException


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


@dataclass(frozen=True)
class ResearchSource:
    title: str
    url: str
    content: str


class WebResearchTools:
    """Keyless web search and page retrieval behind a replaceable tool boundary."""

    def __init__(self, timeout: float = 15.0, max_chars_per_source: int = 1800) -> None:
        self.timeout = timeout
        self.max_chars_per_source = max_chars_per_source
        self.max_response_bytes = 2_000_000

    def search_web(self, query: str, max_results: int = 4) -> list[SearchResult]:
        rows = DDGS(timeout=int(self.timeout)).text(
            query,
            region="wt-wt",
            safesearch="moderate",
            max_results=max_results,
        )
        results: list[SearchResult] = []
        for row in rows:
            url = row.get("href") or row.get("url") or ""
            if not url or not self._is_public_http_url(url):
                continue
            results.append(
                SearchResult(
                    title=row.get("title") or url,
                    url=url,
                    snippet=row.get("body") or "",
                )
            )
        return results

    def scrape_url(self, result: SearchResult) -> ResearchSource:
        if not self._is_public_http_url(result.url):
            raise ValueError("Only public HTTP and HTTPS URLs can be researched.")

        headers = {"User-Agent": "FirstResearchAgent/0.1 (+local educational project)"}
        try:
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=False,
                headers=headers,
            ) as client:
                response = self._get_public_page(client, result.url)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "html" not in content_type and "text" not in content_type:
                    raise ValueError(f"Unsupported content type: {content_type}")
                if len(response.content) > self.max_response_bytes:
                    raise ValueError("Page is larger than the configured retrieval limit.")
                text = self._html_to_text(response.text)
        except (httpx.HTTPError, ValueError):
            text = self._read_with_jina(result.url)

        content = text[: self.max_chars_per_source].strip() or result.snippet
        return ResearchSource(title=result.title, url=result.url, content=content)

    def research(self, query: str, max_sources: int = 3) -> list[ResearchSource]:
        sources: list[ResearchSource] = []
        try:
            results = self.search_web(query, max_results=max_sources + 2)
        except (DDGSException, httpx.HTTPError, OSError):
            return sources

        for result in results:
            try:
                source = self.scrape_url(result)
            except (httpx.HTTPError, ValueError, socket.gaierror):
                if result.snippet:
                    source = ResearchSource(result.title, result.url, result.snippet)
                else:
                    continue
            sources.append(source)
            if len(sources) >= max_sources:
                break
        return sources

    def _read_with_jina(self, url: str) -> str:
        response = httpx.get(
            f"https://r.jina.ai/{url}",
            timeout=self.timeout,
            follow_redirects=True,
            headers={"Accept": "text/plain"},
        )
        response.raise_for_status()
        return response.text

    def _get_public_page(self, client: httpx.Client, url: str) -> httpx.Response:
        current_url = url
        for _ in range(4):
            if not self._is_public_http_url(current_url):
                raise ValueError("Redirect target is not a public HTTP(S) URL.")
            response = client.get(current_url)
            if not response.is_redirect:
                return response
            location = response.headers.get("location")
            if not location:
                raise ValueError("Redirect response did not include a destination.")
            current_url = urljoin(current_url, location)
        raise ValueError("Page exceeded the configured redirect limit.")

    @staticmethod
    def _html_to_text(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "form", "noscript"]):
            element.decompose()
        return " ".join(soup.get_text(" ", strip=True).split())

    @staticmethod
    def _is_public_http_url(url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        if parsed.username or parsed.password:
            return False
        try:
            default_port = 443 if parsed.scheme == "https" else 80
            addresses = socket.getaddrinfo(parsed.hostname, parsed.port or default_port)
        except socket.gaierror:
            return False
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                return False
        return True
