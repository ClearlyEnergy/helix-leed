import requests
from lxml import html
import re
import json
import datetime
"""LEED connect to U.S. GBC GBIG database retrieves score and output values"""

# select between sandbox and production
# URL is currently set to select the HES 2.0 beta
#GBIG_URL = 'https://sandbeta.hesapi.labworks.org/st_api/wsdl' #sandbeta
GBIG_ACTIVITIES = 'http://www.gbig.org/'
GBIG_ADVANCED = 'http://www.gbig.org/search/advanced?&utf8=%E2%9C%94&search[include_non_certified]=0&search[search_type]=Projects&search[text_search_mode]=all&view=list'

# An instance of this class is used to access building records in the LEED
# database from the context of a HES user. 
class LeedHelix:
    def __init__(self):
        self.activities_url = GBIG_ACTIVITIES
        self.search_url = GBIG_ADVANCED

    def __retrieve_list_content(self, page_num, after_date=None, before_date=None):
        """Retrieve GBIG list page content

        For example:
           self.retrieve_list_content(self, page)
        """
        param_string = '&page='+str(page_num)+'&type=advanced&search[place_ids]=6611&search[flat_rating_program_ids]=Certification%2F%2F37'
        if after_date is not None:
            param_string += '&search[after_date]='+after_date.strftime("%Y-%m-%d")

        page = requests.get(self.search_url+param_string)
        tree = html.fromstring(page.content)
        rows = tree.xpath('//div[@class="row result-row"]/div[@class="col-sm-4"]/a/@href')
        return rows

    def __retrieve_total_pages(self, after_date=None, before_date=None):
        """Retrieve GBIG number of properties in region

        For example:
           self.retrieve_list_content(self)
        """
        param_string = '&page=1&type=advanced&search[place_ids]=6611&search[flat_rating_program_ids]=Certification%2F%2F37'        
        if after_date is not None:
            param_string += '&search[after_date]='+after_date.strftime("%Y-%m-%d")
#        
#        &search[before_date]=2018-12-31

        page = requests.get(self.search_url+param_string)
        tree = html.fromstring(page.content)     
        total_entries = tree.xpath('//*[@id="search_form"]/div[3]/div[1]/div/span/text()')
        total_entries = re.findall('(\d+)', total_entries[0])
        if len(total_entries) == 1:
            num_pages = 1
        else:
            num_pages = int(total_entries[2])//25 + 1
        return num_pages
    
    def query_leed_building_ids(self, after_date=None, before_date=None):
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
        num_pages = self.__retrieve_total_pages(after_date=after_date, before_date=before_date)
        building_ids = []
        for page_num in range(1,num_pages+1):
            building_ids += self.__retrieve_list_content(page_num, after_date=after_date, before_date=before_date)

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
        rating = re.match('(LEED-HOMES) (v\d{4}) (Silver|Certified|Gold|Platinum)', rating[0])
        if rating:
            result['green_assessment_name'] = 'LEED for Homes'
            result['green_assessment_property_source'] = 'U.S. Green Building Council'
            result['green_assessment_property_rating'] = rating.group(3)
            result['green_assessment_property_version'] = rating.group(2)
            result['green_assessment_property_url'] = self.activities_url+building_id
        else:
            return {'status': 'error', 'message': 'not rated'}
            
        date = tree.xpath('//p[@class="lead"]/text()')
        date = re.match('\non (\d{2}/\d{2}/\d{4})', date[1])
        result['green_assessment_property_date'] = date
        address = tree.xpath('//address/a/text()')
        if address:
            # use google maps to get zip code
            address = address[0].split(',')
            result['address_line_1'] = address[0].lstrip()
            result['city'] = address[1].lstrip()
            result['state'] = address[2].lstrip()
        
        result['status'] = 'success'
        
        return result
    