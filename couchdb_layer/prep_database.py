#!/usr/bin/env python

from json_layer.request import request
from json_layer.campaign import campaign
from WMCore.Database.CMSCouch import Database
import json


class database:
    class DatabaseNotFoundException(Exception):
        def __init__(self,  db=''):
            self.db = str(db)
        def __str__(self):
            return 'Error: Database ',  self.db,  ' was not found.'
    class DatabaseAccessError(Exception):
        def __init__(self,  db=''):
            self.db = str(db)
        def __str__(self):
            return 'Error: Could not access database ',  self.db
    class DocumentNotFoundException(Exception):
        def __init__(self,  name=''):
            self.name = name
        def __str__(self):
            return 'Error: Document ',  self.name,  ' was not found.'
    class MapReduceSyntaxError(Exception):
        def __init__(self,  query=''):
            self.query = query
        def __str__(self):
            return 'Error: Invalid query "' + self.query + '"'
    class InvalidOperatorError(Exception):
        def __init__(self,  op=''):
            self.op = str(op)
        def __str__(self):
            return 'Error: Operator "' + self.op + '" is invalid.'
    class InvalidParameterError(Exception):
        def __init__(self,  param=''):
            self.param = str(param)
        def __str__(self):
            return 'Error: Invalid Parameter: ' + self.param
            
    def __init__(self,  db_name=''):
        if not db_name:
            raise self.DatabaseNotFoundException(db_name)
        self.db_name = db_name 
        try:    
            self.db = Database(db_name)
        except ValueError as ex:
            print 'Error: Database', db_name,  'could not be accessed or created. Reason:', str(ex)
            raise self.DatabaseAccessError(db_name)
            
        self.allowed_operators = ['<=',  '<',  '>=',  '>',  '==',  '~=']

    def __is_number(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False
       
    def get(self,  prepid=''):
        try:
            return self.db.document(id=prepid)
        except Exception as ex:
            print 'Error: Could not retrieve document: ',  prepid,  '. Reason: ',  str(ex)
            return {}
    
    def __document_exists(self,  doc):
        if not doc:
            return False
        id = ''
        if 'prepid' not in doc:
            if '_id' not in doc:
                return False
            id = doc['_id']
        elif '_id' not in doc:
            if 'prepid' not in doc:
                return False
            id = doc['prepid']
        id = doc['_id']
        return self.__id_exists(prepid=id)

    def document_exists(self, prepid=''):
        return self.__id_exists(prepid) 
    
    def __id_exists(self,  prepid=''):
        try:
            return self.db.documentExists(id=prepid)
        except Exception as ex:
            print 'Error: Could not retrieve document: ',  prepid,  '. Reason: ',  str(ex)
            return False
    
    def delete(self, prepid=''):
        if not prepid:
            return False
        if not self.__id_exists(prepid):
            return False
        try:
            self.db.delete_doc(id=prepid)
            return True
        except Exception as ex:
            print 'Error: Could not delete document:', prepid, '. Reason:', str(ex)
            return False            

    def update(self,  doc={}):
        if self.__document_exists(doc):
            return self.save(doc)
        return False
        
    def update_all(self,  docs=[]):
        if not docs:
            return False
            
        for doc in docs:
            if self.__document_exists(doc):
                self.db.queue(doc)
        try:
            self.db.commit()
            return True
        except Exception as ex:
            print 'Error: Could not commit changes to database. Reason: ',  str(ex)
            return False        
        
    def get_all(self, page_num=0): 
        try:
            limit, skip = self.__pagify(page_num)
            if limit >= 0 and skip >= 0: 
                return self.db.loadView(self.db_name, "all", options={'limit':limit,'skip':skip})['rows']
            return self.db.loadView(self.db_name, "all")['rows']
        except Exception as ex:
            print 'Error: Could not access view. Reason:',  str(ex)
            return []

    
    def query(self,  query='', page_num=0):
        if not query:
            return self.get_all()
        try:   
            return self.__query(query, page=page_num)
        except Exception as ex:
            print 'Error: An error occured while trying to load a view. Reason:',  str(ex)
            return []

    def __extract_operators(self,  query=''):
        if not query:
            return ()
        clean = []
        tokens = []
        for op in self.allowed_operators:
            if op in query:
                tokens = query.rsplit(op)
                tokens.insert(1,  op)
            else:
                continue
            for tok in tokens:
                if len(tok) < 1:
                    continue
                clean.append(tok.strip().strip('"'))
            if len(clean) != 3:
                raise self.MapReduceSyntaxError(query)
            #if clean[0] not in self.request and clean[1] not in self.campaign:
            #    raise self.IllegalParameterError(clean[0])
            return clean
        raise self.MapReduceSyntaxError(query)
    
    def __pagify(self, page_num=0, limit=20):
        if page_num < 0:
            return -1,0
        skip = limit*page_num
        return limit, skip      
    
    def __execute_query(self, tokenized_query='', page=-1, limit=20):
            tokens = []
            try:
                tokens = self.__extract_operators(tokenized_query)
            except Exception as ex:
                print str(ex)
                return []
            if tokens:
                view_name, view_opts = self.__build_query(tokens)
                if not view_name or not view_opts:
                    return []
                if page > -1:
                    view_opts['limit']=limit
                    view_opts['skip']=page*limit                    
                return self.db.loadView(self.db_name, view_name, options=view_opts)['rows']
            else:
                return []
    
    def raw_query(self,  view_name,  options={}):
        return self.db.loadView(self.db_name,  view_name,  options)['rows']
                
    def __get_op(self, oper):
        if oper == '>':
            return lambda x,y: x > y
        elif oper == '>=':
            return lambda x,y: x >= y
        elif oper == '<':
            return lambda x,y: x < y
        elif oper == '<=':
            return lambda x,y: x <= y
        elif oper == '==':
            return lambda x,y: x == y       
        else:
            return None     
        
    def __filter(self, tokenized_query=[], view_results=[]):
        if len(tokenized_query) != 3:
            return view_results
        prn = tokenized_query[0]
        op = tokenized_query[1]
        if self.__is_number(tokenized_query[2]):
            val = float(tokenized_query[2])
        else:
            val = tokenized_query[2]
        f = self.__get_op(op)
        return filter(lambda x: f(x[prn],val), view_results)    

    def __query(self, query='', page=0, limit=20):
        t_par = []
        results = []
        if ',' in query:
             t_par = query.rsplit(',')
        if not t_par:
             t_par = [query]
        if len(t_par) == 1:          
            return self.__execute_query(t_par[0], page, limit)#[page*limit:page*limit+limit]
        elif len(t_par) == 0:
            return []

        temp = self.__execute_query(t_par[0])#[page*limit:page*limit+limit]
        res = map(lambda x: x['value'], temp) 
        print len(res)
        if len(res) == 0:
            return []
        for i in range(1,len(t_par)):
            tq = self.__extract_operators(t_par[i])
            res = self.__filter(tq, res)
        return map(lambda x: {'value':x},res[page*limit:page*limit+20])
                    
    def __build_query(self,tokens=[]):
        if not tokens:
            return None,None
        if len(tokens) != 3:
            raise self.MapReduceSyntaxError(tokens)
        param = tokens[0]
        op = tokens[1]     
        kval = tokens[2]
        try:
            view_opts = self.__build_options(op, kval)
        except Exception as ex:
            print 'Error: value types are not compatible with operator:', op
            return None,None
        return param, view_opts
    
    def __build_options(self,op, val):
        def is_number(s):
            try:
                float(s)
                return True
            except ValueError:
                return False
        
        # options dictionary
        opts = {} 
        
        # default the composite key search
        if '[' in val and ']' in val:
            if op == '==':
                opts['key'] = val
            return opts
        
        # handle alphanumeric key ranges
        num_flag = False
        if is_number(val):
            num_flag = True
            kval = int(val)
        else:
            kval = val.decode('ascii')
        if '>' in op:
            if '=' in op:
                opts['startkey']=kval
            else:
                if num_flag:
                    opts['startkey']=kval+1
                else:
                    opts['startkey']=kval
            if num_flag:
                opts['endkey']=99999999 # assume its numeric
            else:
                opts['endkey']=kval+u'\u9999'
        elif '<' in op:
            if '=' in op:
                opts['endkey']=kval
            else:
                if num_flag:
                    opts['endkey']=kval-1
                else:
                    opts['endkey']=kval
            if num_flag:
                opts['startkey']=-99999999
            else:
                opts['startkey']=''
                
        elif '==' == op:
            opts['key']=kval
        elif '~=' == op:
            if kval[-1] == '*':
                opts['startkey']=kval[:len(kval)-1]
                opts['endkey']=kval[:len(kval)-1]+u'\u9999'#'99999999'#'\u9999'
        return opts
            
  
    def save_all(self,  docs=[]):
        if not docs:
            return False
        for doc in docs:
            self.db.queue(doc)
        try:
            self.db.commit()
            return True
        except Exception as ex:
            print 'Error: Could not commit changes to database. Reason: ',  str(ex)
            return False

    def save(self, doc={}):
        if not doc:
            return False
        try:
            self.db.commitOne(doc)
            return True
        except Exception as ex:
            print 'Error: Could not commit changes to database. Reason: ', str(ex)
            return False

    def count(self):
        try:
            return len(self.db.allDocs()) 
        except Exception as ex:
            print 'Error: Could not count documents in database. Reason:', str(ex)
            return -1 

#db = database('requests')
#f = open('up_prepdb_json/requests', 'r')
#lines = f.readlines()
#f.close()
#obs = []
#for line in lines:
#    if len(line) < 2:
#        continue
#    ob = json.loads(line)
#    ob['_id'] = ob['prepid']
#    ob['member_of_campaign'] = ob['prepid'].rsplit('-')[1]
#   obs.append(ob)
#print 'requests:', db.save_all(obs)

#db = database('campaigns')
#f = open('up_prepdb_json/campaigns', 'r')
#lines = f.readlines()
#f.close()
#obs = []
#for line in lines:
#    if len(line) < 2:
#        continue
#    ob = json.loads(line)
#    ob['_id'] = ob['prepid']
#    obs.append(ob)
#print 'campaigns:',db.save_all(obs)


