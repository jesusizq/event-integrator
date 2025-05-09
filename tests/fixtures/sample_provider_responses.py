SAMPLE_XML_RESPONSE_1 = """<?xml version="1.0" encoding="UTF-8"?>
<planList xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0" xsi:noNamespaceSchemaLocation="planList.xsd">
   <output>
      <base_plan base_plan_id="291" sell_mode="online" title="Camela en concierto">
         <plan plan_start_date="2021-06-30T21:00:00" plan_end_date="2021-06-30T22:00:00" plan_id="291" sell_from="2020-07-01T00:00:00" sell_to="2021-06-30T20:00:00" sold_out="false">
            <zone zone_id="40" capacity="243" price="20.00" name="Platea" numbered="true" />
            <zone zone_id="38" capacity="100" price="15.00" name="Grada 2" numbered="false" />
            <zone zone_id="30" capacity="90" price="30.00" name="A28" numbered="true" />
         </plan>
      </base_plan>
      <base_plan base_plan_id="322" sell_mode="online" organizer_company_id="2" title="Pantomima Full">
         <plan plan_start_date="2021-02-10T20:00:00" plan_end_date="2021-02-10T21:30:00" plan_id="1642" sell_from="2021-01-01T00:00:00" sell_to="2021-02-09T19:50:00" sold_out="false">
            <zone zone_id="311" capacity="2" price="55.00" name="A42" numbered="true" />
         </plan>
         <plan plan_start_date="2021-02-11T20:00:00" plan_end_date="2021-02-11T21:30:00" plan_id="1643" sell_from="2021-01-01T00:00:00" sell_to="2021-02-10T19:50:00" sold_out="false">
            <zone zone_id="311" capacity="2" price="55.00" name="A42" numbered="true" />
         </plan>
      </base_plan>
      <base_plan base_plan_id="1591" sell_mode="online" organizer_company_id="1" title="Los Morancos">
         <plan plan_start_date="2021-07-31T20:00:00" plan_end_date="2021-07-31T21:00:00" plan_id="1642" sell_from="2021-06-26T00:00:00" sell_to="2021-07-31T19:50:00" sold_out="false">
            <zone zone_id="186" capacity="2" price="75.00" name="Amfiteatre" numbered="true" />
            <zone zone_id="186" capacity="16" price="65.00" name="Amfiteatre" numbered="false" />
         </plan>
      </base_plan>
   </output>
</planList>
"""

EMPTY_XML_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<planList xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0" xsi:noNamespaceSchemaLocation="planList.xsd">
   <output>
   </output>
</planList>
"""

SAMPLE_XML_RESPONSE_2_SUBSET = """<?xml version="1.0" encoding="UTF-8"?>
<planList xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0" xsi:noNamespaceSchemaLocation="planList.xsd">
   <output>
      <base_plan base_plan_id="291" sell_mode="online" title="Camela en concierto">
         <plan plan_start_date="2021-06-30T21:00:00" plan_end_date="2021-06-30T22:00:00" plan_id="291" sell_from="2020-07-01T00:00:00" sell_to="2021-06-30T20:00:00" sold_out="false">
            <zone zone_id="40" capacity="240" price="20.00" name="Platea" numbered="true" />
            <zone zone_id="38" capacity="50" price="15.00" name="Grada 2" numbered="false" />
            <zone zone_id="30" capacity="90" price="30.00" name="A28" numbered="true" />
         </plan>
      </base_plan>
      <base_plan base_plan_id="1591" sell_mode="online" organizer_company_id="1" title="Los Morancos - Updated">
         <plan plan_start_date="2021-07-31T20:00:00" plan_end_date="2021-07-31T21:20:00" plan_id="1642" sell_from="2021-06-26T00:00:00" sell_to="2021-07-31T19:50:00" sold_out="false">
            <zone zone_id="186" capacity="0" price="75.00" name="Amfiteatre" numbered="true" />
            <zone zone_id="186" capacity="14" price="65.00" name="Amfiteatre" numbered="false" />
         </plan>
      </base_plan>
   </output>
</planList>
"""
