"""
Validation utilities for XTream credentials
"""

import asyncio
import json
from typing import Optional, Dict, List

import aiohttp
from rich.progress import Progress, SpinnerColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn, TextColumn
from models import XtreamCredential
from datetime import datetime

class XtreamValidator:
    """Validates XTream API credentials"""
    
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.user_agent = 'XTream-Validator/1.0'
        self.verbose = False
    
    async def _validate_credential_async(self, credential: XtreamCredential, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> bool:
        """Validate a single XTream credential asynchronously using aiohttp."""
        # Build player_api.php URL from get.php URL
        validation_url = credential.xtream_url.replace('get.php', 'player_api.php')

        async with semaphore:
            try:
                async with session.get(validation_url, timeout=self.timeout) as response:
                    if response.status == 200:
                        try:
                            data = await response.json(content_type=None)
                        except Exception:
                            credential.is_valid = False
                            credential.validation_date = datetime.now()
                            print(f"    ✗ Invalid JSON: {credential.domain}:{credential.port}/{credential.username}")
                            return False

                        if 'user_info' in data and data['user_info'].get('auth') == 1:
                            credential.is_valid = True
                            credential.validation_date = datetime.now()
                            credential.user_info = data['user_info']
                            if self.verbose:
                                print(f"    ✓ Valid: {credential.domain}:{credential.port}/{credential.username}")
                            return True

                    credential.is_valid = False
                    credential.validation_date = datetime.now()
                    if self.verbose:
                        print(f"    ✗ Invalid: {credential.domain}:{credential.port}/{credential.username}")
                    return False

            except asyncio.TimeoutError:
                credential.is_valid = False
                credential.validation_date = datetime.now()
                if self.verbose:
                    print(f"    ✗ Timeout: {credential.domain}:{credential.port}/{credential.username}")
                return False
            except aiohttp.ClientError as e:
                credential.is_valid = False
                credential.validation_date = datetime.now()
                if self.verbose:
                    print(f"    ✗ Error: {credential.domain}:{credential.port}/{credential.username} - {str(e)[:50]}")
                return False

    async def _validate_credentials_async(self, credentials: list[XtreamCredential], progress: Progress, task_id: int) -> list[XtreamCredential]:
        """Internal async implementation for validating multiple credentials.

        The rich Progress instance and task_id are provided by the synchronous
        wrapper so that validation progress can be displayed in-place.
        """
        total = len(credentials)

        if total == 0:
            return []

        valid_credentials: List[XtreamCredential] = []

        # Limit concurrent validations to avoid hammering servers
        max_concurrent = min(20, total)
        semaphore = asyncio.Semaphore(max_concurrent)

        timeout = aiohttp.ClientTimeout(total=self.timeout)
        headers = {'User-Agent': self.user_agent}

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            tasks = [
                self._validate_credential_async(cred, session, semaphore)
                for cred in credentials
            ]

            results = []
            for coro in asyncio.as_completed(tasks):
                ok = await coro
                results.append(ok)
                # Advance the progress bar after each completed validation
                progress.update(task_id, advance=1)

        # Zip may truncate if lengths differ; use index
        for idx, cred in enumerate(credentials):
            if idx < len(results) and results[idx]:
                valid_credentials.append(cred)

        return valid_credentials

    def validate_credentials(self, credentials: list[XtreamCredential]) -> list[XtreamCredential]:
        """Public synchronous wrapper for async credential validation.

        Uses rich Progress to present a static, in-place view of validation
        progress while asyncio/aiohttp performs the HTTP work concurrently.
        """
        total = len(credentials)

        if total == 0:
            print("\n=== VALIDATING 0 CREDENTIALS ===")
            return []

        print(f"\n=== VALIDATING {total} CREDENTIALS ===")

        # Configure a compact, readable progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold green]Validating[/bold green]"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        ) as progress:
            task_id = progress.add_task("validation", total=total)

            try:
                valid_credentials = asyncio.run(
                    self._validate_credentials_async(credentials, progress, task_id)
                )
            except KeyboardInterrupt:
                # Graceful shutdown on Ctrl+C
                print("\n⚠️  Validation interrupted by user (Ctrl+C)")
                # Return whatever has been marked so far
                valid_credentials = [c for c in credentials if c.is_valid]

        print(f"\nValidation complete: {len(valid_credentials)}/{total} credentials are valid")
        return valid_credentials
