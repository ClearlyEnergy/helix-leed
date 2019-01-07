import requests
from lxml import html
import re
import json
import datetime
import googlemaps
import os

"""LEED connect to U.S. GBC GBIG database retrieves score and output values"""

GBIG_ACTIVITIES = 'http://www.gbig.org'
GBIG_ADVANCED = 'http://www.gbig.org/search/advanced?&utf8=%E2%9C%94&search[include_non_certified]=0&search[search_type]=Projects&search[text_search_mode]=all&view=list'

# An instance of this class is used to access building records on the LEED web site
class LeedHelix:
    def __init__(self):
        self.activities_url = GBIG_ACTIVITIES
        self.search_url = GBIG_ADVANCED
        self.gmaps = googlemaps.Client(os.environ.get('GOOGLEMAPS_KEY', ''))

    def __retrieve_list_content(self, page_num, geo_id, after_date=None, before_date=None):
        """Retrieve GBIG list page content

        For example:
           self.retrieve_list_content(self, page)
        """
        param_string = '&page='+str(page_num)+'&type=advanced&search[place_ids]='+geo_id+'&search[flat_rating_program_ids]=Certification%2F%2F37'
        if after_date is not None:
            param_string += '&search[after_date]='+after_date.strftime("%Y-%m-%d")
        if before_date is not None:
            param_string += '&search[before_date]='+before_date.strftime("%Y-%m-%d")

        page = requests.get(self.search_url+param_string)
        tree = html.fromstring(page.content)
        certificates = tree.xpath('//div[@class="row result-row"]/div[@class="col-sm-3"]/div[contains(@class,"cert-badge")]/text()')
        rows = tree.xpath('//div[@class="row result-row"]/div[@class="col-sm-4"]/a/@href')
        # removes rows which are only registered and not certified buildings
        registered_indices = [i for i, e in enumerate(certificates) if e == 'Registered']
        rows = [x for i,x in enumerate(rows) if i not in registered_indices]        
        return rows

    def __retrieve_total_pages(self, geo_id, after_date=None, before_date=None):
        """Retrieve GBIG number of properties in region

        For example:
           self.retrieve_list_content(self)
        """
        param_string = '&page=1&type=advanced&search[place_ids]='+geo_id+'&search[flat_rating_program_ids]=Certification%2F%2F37'        
        if after_date is not None:
            param_string += '&search[after_date]='+after_date.strftime("%Y-%m-%d")
        if before_date is not None:
            param_string += '&search[before_date]='+before_date.strftime("%Y-%m-%d")

        page = requests.get(self.search_url+param_string)
        tree = html.fromstring(page.content)     
        total_entries = tree.xpath('//*[@id="search_form"]/div[3]/div[1]/div/span/text()')
        if not total_entries:
            return None
        else:
            total_entries = re.findall('(\d*,*\d+)', total_entries[0])
            if len(total_entries) == 1:
                num_pages = 1
            else:
                num_pages = int(total_entries[2].replace(',',''))//25 + 1
            return num_pages
    
    def query_leed_building_ids(self, geo_id, after_date=None, before_date=None):
        """query_leed_building_ids
        Parameters:
            Geography: Geographic parameter to narrow search by, typically State
            after_date: optional, retrieve only records created on or after start date, format 'yyyy-mm-dd'
            before_date: optional, retrieve only records created before end date, use only in conunction with start date

        Returns:
            list of ids
        For example:
           client.query_leed_buildling_ids('MA')
        """        
        num_pages = self.__retrieve_total_pages(geo_id=geo_id, after_date=after_date, before_date=before_date)
        building_ids = []
        if num_pages is not None:
            for page_num in range(1,num_pages+1):
                building_ids += self.__retrieve_list_content(page_num, geo_id=geo_id, after_date=after_date, before_date=before_date)
            
        return building_ids
        
    def query_leed(self, building_id):
        """ Returns primary LEED for homes parameters for a building page ID. 
        Parameters:
            building_id: LEED building id

        Returns:
            dictionary with street address, city, state, zip code, year built, conditioned floor area, LEED rating, LEED Score
        
        For example:
           client.query_leed('/activities/leed-10391892')
        """
        result = {}
        page = requests.get(self.activities_url+building_id)
        tree = html.fromstring(page.content)
        
        title = tree.xpath('//h1/text()')
        if title[0] == "Hmm, the page you're looking for can't be found.":
            return {'status': 'error', 'message': title[0]}            
        
        rating = tree.xpath('//p[@class="lead"]/strong/text()')
        rating = re.match('(LEED-HOMES).* (v\d{4}) (Silver|Certified|Gold|Platinum)', rating[0])
        if rating:
            result['Green Assessment Name'] = 'LEED for Homes'
            result['Green Assessment Property Source'] = 'U.S. Green Building Council'
            result['Green Assessment Property Rating'] = rating.group(3).upper()
            result['Green Assessment  Property Version'] = rating.group(2)
            result['Green Assessment Property Url'] = self.activities_url+building_id
        else:
            return {'status': 'error', 'message': 'not rated'}
            
        date = tree.xpath('//p[@class="lead"]/text()')
        date = re.match('\non (\d{2}/\d{2}/\d{4})', date[1])
        result['Green Assessment Property Date'] = date.group(1)
        
        rating = tree.xpath('//h2[@class="points-achieved"]/span/text()')
        result['Green Assessment Property Extra Data'] = {'leed_score': rating[0]+'/'+rating[1]}
        
        property_type = tree.xpath('//table[@class="table"]/tr[th//text()[contains(., "Space Type")]]/td/text()')
        if property_type:
            result['property_type'] = property_type[0]
        
        address = tree.xpath('//address/a/text()')
        
        if address:
            # use google maps to get zip code
            address = address[0].split(',')
            num_elem = len(address)
            if num_elem < 4:
                    return {'status': 'error', 'message': 'address could not be parsed'}
#            result['address_line_1'] = address[num_elem-4].lstrip()
            if address[0].lstrip() == 'InSite':
                result['address_line_1'] = address[1].lstrip()
            else:
                result['address_line_1'] = address[0].lstrip()
            result['city'] = address[num_elem-3].lstrip()
            result['state'] = address[num_elem-2].lstrip()
            
            # geocode results and add zip code
            if result['address_line_1'] and result['city'] and result['state']:
                geocode_result = self.gmaps.geocode(",".join([result['address_line_1'], result['city'], result['state']]))
                if geocode_result:
                    for comp in geocode_result[0]['address_components']:
                        if 'postal_code' in comp['types']:
                            result['postal_code'] = comp['short_name']
                            break
                    #reject results with "APPROXIMATE" or "RANGE_INTERPOLATED" location_type
                    if geocode_result[0]['geometry']['location_type'] in ('ROOFTOP','GEOMETRIC_CENTER'):
                        result['latitude'] = geocode_result[0]['geometry']['location']['lat']
                        result['longitude'] = geocode_result[0]['geometry']['location']['lng']
        
        result['status'] = 'success'
        
        return result
    