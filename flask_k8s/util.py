import json
from datetime import date, datetime
import decimal


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

class JsonUtil:
    
    def __default(self,obj):      
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')        
        else:
            raise TypeError('%r is not JSON serializable' % obj)

      
    def parseJsonObj(self,obj):
        jsonstr=json.dumps(obj,default=self.__default,ensure_ascii=False) #cls=DecimalEncoder
        return jsonstr
    
    def parseJsonString(self,jsonstring):
        obj=json.loads(jsonstring)
        return obj