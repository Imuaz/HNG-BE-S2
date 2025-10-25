import requests
import random
from decimal import Decimal
from typing import Dict, List, Optional
from django.utils import timezone
from .models import Country

class ExternalAPIError(Exception):
    """Custom exception for external API failures"""
    pass


class CountryService:
    """
    Handles all business logic for country data.
    
    This includes:
    - Fetching from external APIs
    - Computing estimated GDP
    - Updating/creating database records
    """
    
    COUNTRIES_API = "https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies"
    EXCHANGE_API = "https://open.er-api.com/v6/latest/USD"
    REQUEST_TIMEOUT = 10  # seconds
    
    @staticmethod
    def fetch_countries() -> List[Dict]:
        """
        Fetch country data from REST Countries API.
        
        Returns:
            List of country dictionaries
            
        Raises:
            ExternalAPIError: If API call fails
        """
        try:
            response = requests.get(
                CountryService.COUNTRIES_API,
                timeout=CountryService.REQUEST_TIMEOUT
            )
            response.raise_for_status()  # Raises HTTPError for bad status codes
            return response.json()
        except requests.RequestException as e:
            raise ExternalAPIError(f"Could not fetch data from REST Countries API: {str(e)}")
    
    @staticmethod
    def fetch_exchange_rates() -> Dict[str, float]:
        """
        Fetch exchange rates from Exchange Rate API.
        
        Returns:
            Dictionary mapping currency codes to rates
            Example: {"NGN": 1600.23, "GHS": 15.34}
            
        Raises:
            ExternalAPIError: If API call fails
        """
        try:
            response = requests.get(
                CountryService.EXCHANGE_API,
                timeout=CountryService.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            return data.get('rates', {})
        except requests.RequestException as e:
            raise ExternalAPIError(f"Could not fetch data from Exchange Rate API: {str(e)}")
    
    @staticmethod
    def calculate_estimated_gdp(
        population: int,
        exchange_rate: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        Calculate estimated GDP using the formula:
        GDP = population × random(1000-2000) ÷ exchange_rate
        
        Args:
            population: Country population
            exchange_rate: Currency exchange rate (or None)
            
        Returns:
            Estimated GDP as Decimal, or None if calculation not possible
        """
        if not exchange_rate or exchange_rate == 0:
            return None
        
        # Generate random multiplier between 1000 and 2000
        multiplier = random.uniform(1000, 2000)
        
        # Calculate: population × multiplier ÷ exchange_rate
        gdp = Decimal(str(population)) * Decimal(str(multiplier)) / exchange_rate
        
        # Round to 2 decimal places
        return gdp.quantize(Decimal('0.01'))
    
    @staticmethod
    def extract_currency_code(currencies: List[Dict]) -> Optional[str]:
        """
        Extract first currency code from currencies array.
        
        Args:
            currencies: List of currency objects from API
            Example: [{"code": "NGN", "name": "Nigerian naira"}]
            
        Returns:
            Currency code (e.g., "NGN") or None
        """
        if not currencies or not isinstance(currencies, list):
            return None
        
        # Get first currency's code
        first_currency = currencies[0]
        return first_currency.get('code')
    
    @classmethod
    def refresh_countries(cls) -> Dict:
        """
        Main method to refresh all country data.
        
        This method:
        1. Fetches countries from external API
        2. Fetches exchange rates
        3. Processes each country
        4. Updates or creates database records
        
        Returns:
            Dictionary with status information
            
        Raises:
            ExternalAPIError: If any external API fails
        """
        # Step 1: Fetch external data
        countries_data = cls.fetch_countries()
        exchange_rates = cls.fetch_exchange_rates()
        
        # Track results
        updated_count = 0
        created_count = 0
        refresh_time = timezone.now()
        
        # Step 2: Process each country
        for country_data in countries_data:
            # Extract fields
            name = country_data.get('name', '').strip()
            if not name:
                continue  # Skip countries without name
            
            capital = country_data.get('capital')
            region = country_data.get('region')
            population = country_data.get('population', 0)
            flag_url = country_data.get('flag')
            currencies = country_data.get('currencies', [])
            
            # Extract currency code
            currency_code = cls.extract_currency_code(currencies)
            
            # Get exchange rate if currency exists
            exchange_rate = None
            if currency_code:
                rate_value = exchange_rates.get(currency_code)
                if rate_value:
                    exchange_rate = Decimal(str(rate_value))
            
            # Calculate GDP
            estimated_gdp = cls.calculate_estimated_gdp(population, exchange_rate)
            
            # Step 3: Update or create database record
            country, created = Country.objects.update_or_create(
                name__iexact=name,  # Case-insensitive match
                defaults={
                    'name': name,
                    'capital': capital,
                    'region': region,
                    'population': population,
                    'currency_code': currency_code,
                    'exchange_rate': exchange_rate,
                    'estimated_gdp': estimated_gdp if estimated_gdp else Decimal('0'),
                    'flag_url': flag_url,
                    'last_refreshed_at': refresh_time
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        return {
            'total_countries': created_count + updated_count,
            'created': created_count,
            'updated': updated_count,
            'last_refreshed_at': refresh_time
        }