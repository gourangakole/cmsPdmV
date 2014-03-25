#!/usr/bin/env python

import cherrypy
from json import dumps
from couchdb_layer.mcm_database import database
from RestAPIMethod import RESTResource
from ChainedRequestPrepId import ChainedRequestPrepId
from json_layer.chained_request import chained_request
from json_layer.chained_campaign import chained_campaign
from json_layer.request import request
from json_layer.action import action
from tools.user_management import access_rights
from tools.json import threaded_loads

"""
## import the rest api for wilde request search and dereference to chained_requests using member_of_chain
class SearchChainedRequest(RESTResource):
    def __init__(self):
        self.access_limit = access_rights.user
        self.getter

    def PUT(self):
"""        


class CreateChainedRequest(RESTResource):
    def __init__(self):
        self.db_name = 'chained_requests'
        self.access_limit = access_rights.administrator

    def PUT(self):
        """
        Create a chained request from the provided json content
        """
        return dumps(self.import_request(cherrypy.request.body.read().strip()))

    def import_request(self, data):
        db = database(self.db_name)
        json_input=threaded_loads(data)
        if 'pwg' not in json_input or 'member_of_campaign' not in json_input:
            self.logger.error('Now pwg or member of campaign attribute for new chained request')
            return {"results":False}
        if 'prepid' in json_input:
            req = chained_request(json_input)
            cr_id = req.get_attribute('prepid')
        else:
            cr_id = ChainedRequestPrepId().next_id(json_input['pwg'], json_input['member_of_campaign'])
            if not cr_id:
                return {"results":False}
            req = chained_request(db.get(cr_id))

        for key in json_input:
            if key not in ['prepid', '_id', '_rev', 'history']:
                req.set_attribute(key, json_input[key])

        if not req.get_attribute('prepid'):
            self.logger.error('prepid returned was None')
            raise ValueError('Prepid returned was None')


        self.logger.log('Created new chained_request %s' % cr_id)

        # update history with the submission details
        req.update_history({'action': 'created'})

        return self.save_request(db, req)

    def save_request(self, db, req):
        if not db.document_exists(req.get_attribute('_id')):
            if db.save(req.json()):
                self.logger.log('new chained_request successfully saved.')
                return {"results":True}
            else:
                self.logger.error('Could not save new chained_request to database')
                return {"results":False}
        else:
            if db.update(req.json()):
                self.logger.log('new chained_request successfully saved.')
                return {"results":True}
            else:
                self.logger.error('Could not save new chained_request to database')
                return {"results":False}

class UpdateChainedRequest(RESTResource):
    def __init__(self):
        self.db_name = 'chained_requests'
        self.access_limit = access_rights.administrator

    def PUT(self):
        """
        Update a chained request from the provided json content
        """
        return dumps(self.update_request(cherrypy.request.body.read().strip()))

    def update_request(self, data):
        try:
            req = chained_request(json_input=threaded_loads(data))
        except chained_request.IllegalAttributeName as ex:
            return {"results":False}

        if not req.get_attribute('prepid') and not req.get_attribute('_id'):
            self.logger.error('prepid returned was None') 
            raise ValueError('Prepid returned was None')
            #req.set_attribute('_id', req.get_attribute('prepid')

        self.logger.log('Updating chained_request %s' % (req.get_attribute('_id')))

        # update history
        req.update_history({'action': 'update'})

        return self.save_request(req)

    def save_request(self, req):
        db = database(self.db_name)
        return {"results": db.update(req.json())}


class DeleteChainedRequest(RESTResource):
    def __init__(self):
        self.access_limit = access_rights.production_manager

    def DELETE(self, *args):
        """
        Simply delete a chained requests
        """
        if not args:
            return dumps({"results":False})
        return dumps(self.delete_request(args[0]))

    def delete_request(self, crid):

        crdb = database('chained_requests')
        rdb = database('requests')
        adb = database('actions')
        mcm_cr = chained_request(crdb.get(crid))
        mcm_a = None
        ## get all objects
        mcm_r_s=[]
        for (i,rid) in enumerate(mcm_cr.get_attribute('chain')):
            mcm_r = request(rdb.get(rid))
            #this is not a valid check as it is allowed to remove a chain around already running requests
            #    if mcm_r.get_attribute('status') != 'new':
            #        return {"results":False,"message" : "the request %s part of the chain %s for action %s is not in new status"%( mcm_r.get_attribute('prepid'),
            #                                                                                                                             crid,
            #                                                                                                                             mcm_a.get_attribute('prepid'))}
            in_chains = mcm_r.get_attribute('member_of_chain')
            in_chains.remove( crid )
            mcm_r.set_attribute('member_of_chain', in_chains)
            if i==0:
                # the root is the action id
                mcm_a = action(adb.get(rid))
                if len(in_chains)==0 and mcm_r.get_attribute('status')!='new':
                    return {"results":False,"message" : "the request %s, not in status new, at the root of the chain will not be chained anymore"% rid}
            else:
                if len(in_chains)==0:
                    return {"results":False,"message" : "the request %s, not at the root of the chain will not be chained anymore"% rid}

            mcm_r.update_history({'action':'leave','step':crid})
            mcm_r_s.append( mcm_r )

        ## check if possible to get rid of it !
        # action for the chain is disabled
        chains = mcm_a.get_chains( mcm_cr.get_attribute('member_of_campaign'))
        if chains[crid]['flag']:
            return {"results":False,"message" : "the action %s for %s is not disabled"%(mcm_a.get_attribute('prepid'), crid)}
        #take it out
        mcm_a.remove_chain(  mcm_cr.get_attribute('member_of_campaign'), mcm_cr.get_attribute('prepid') )

        if not adb.update( mcm_a.json()):
            return {"results":False,"message" : "Could not save action "+ mcm_a.get_attribute('prepid')}
        ## then save all changes
        for mcm_r in mcm_r_s:
            if not rdb.update( mcm_r.json()):
                return {"results":False,"message" : "Could not save request "+ mcm_r.get_attribute('prepid')}
            else:
                mcm_r.notify("Request {0} left chain".format( mcm_r.get_attribute('prepid')),
                             "Request {0} has successfuly left chain {1}".format( mcm_r.get_attribute('prepid'), crid))

        return {"results": crdb.delete(crid)}


class GetChainedRequest(RESTResource):
    def __init__(self):
        self.db_name = 'chained_requests'

    def GET(self, *args):
        """
        Retrieve the content of a chained request id
        """
        if not args:
            self.logger.error('No arguments were given')
            return dumps({"results":{}})
        return dumps(self.get_request(args[0]))

    def get_request(self, data):
        db = database(self.db_name)
        if ',' in data:
            rlist = data.rsplit(',')
            res = []
            for rid in rlist:
                tmp_data = db.get(prepid=rid)
                if len(tmp_data) > 0:
                    res.append(tmp_data)
            return {"results": res}
        else:
            return {"results": db.get(prepid=data)}


# REST method that makes the chained request flow to the next
# step of the chain
class FlowToNextStep(RESTResource):
    def __init__(self):
        self.access_limit = access_rights.production_manager

    def PUT(self):
        """
        Allows to flow a chained request with the dataset and blocks provided in the json 
        """
        return dumps(self.flow2(cherrypy.request.body.read().strip()))

    def GET(self, *args):
        """
        Allow to flow a chained request with internal information
        """
        if not args:
            self.logger.error('No arguments were given.')
            return dumps({"results":'Error: No arguments were given.'})
        check_stats=True
        reserve = False
        if len(args)>1:
            check_stats=(args[1]!='force')
            self.logger.log(args)
            reserve = args[1]=='reserve'
        return dumps(self.multiple_flow(args[0], check_stats, reserve))

    def multiple_flow(self, rid, check_stats=True, reserve=False):
        if ',' in rid:
            rlist = rid.rsplit(',')
            res = []
            for r in rlist:
                 res.append(self.flow(r, check_stats=check_stats, reserve = reserve))
            return res
        else:
            return self.flow(rid, check_stats=check_stats, reserve = reserve)

    def flow2(self,  data):
        try:
            vdata = threaded_loads(data)
        except ValueError as ex:
            self.logger.error('Could not start flowing to next step. Reason: %s' % (ex)) 
            return {"results":str(ex)}
        db = database('chained_requests')
        try:
            creq = chained_request(json_input=db.get(vdata['prepid']))
        except Exception as ex:
            self.logger.error('Could not initialize chained_request object. Reason: %s' % (ex))
            return {"results":str(ex)}

        self.logger.log('Attempting to flow to next step for chained_request %s' %  (creq.get_attribute('_id')))

        # if the chained_request can flow, do it
        inputds = ''
        inblack = []
        inwhite = []
        if 'input_dataset' in vdata:
            inputds = vdata['input_dataset']
        if 'block_black_list' in vdata:
            inblack = vdata['block_black_list']
        if 'block_white_list' in vdata:
            inwhite = vdata['block_white_list']
        if 'force' in vdata:
            check_stats = vdata['force']!='force'
        if 'reserve' in vdata and vdata["reserve"]:
            return creq.reserve()
        return creq.flow_trial( inputds,  inblack,  inwhite, check_stats)

    def flow(self, chainid, check_stats=True, reserve = False):
        try:
            db = database('chained_requests')
            creq = chained_request(json_input=db.get(chainid))
        except Exception as ex:
            self.logger.error('Could not initialize chained_request object. Reason: %s' % (ex)) 
            return {"results":str(ex)}


        # if the chained_request can flow, do it
        if reserve:
            self.logger.log('Attempting to reserve to next step for chained_request %s' %  (creq.get_attribute('_id')))
            return creq.reserve()
        self.logger.log('Attempting to flow to next step for chained_request %s' %  (creq.get_attribute('_id')))
        return creq.flow_trial(check_stats=check_stats)

class RewindToPreviousStep(RESTResource):
    def __init__(self):
        self.access_limit = access_rights.production_manager

    def GET(self,  *args):
        """
        Rewind the provided coma separated chained requests of one step.
        """
        if not len(args):
            return dumps({"results":False})

        res=[]

        crids=args[0].split(",")
        for crid in crids:
            res.append( self.rewind_one( crid ) )

        if len(res)!=1:
            return dumps(res)
        else:
            return dumps(res[0])

    def rewind_one(self, crid):
        crdb = database('chained_requests')
        rdb = database('requests')
        if not crdb.document_exists( crid ):
            return {"results":False, "message":"does not exist","prepid" : crid}
        mcm_cr = chained_request( crdb.get( crid) )
        current_step = mcm_cr.get_attribute('step')
        if current_step==0:
            ## or should it be possible to cancel the initial requests of a chained request
            return {"results":False, "message":"already at the root","prepid" : crid}

        ## supposedly all the other requests were already reset!
        for next in mcm_cr.get_attribute('chain')[current_step+1:]:
            ## what if that next one is not in the db
            if not rdb.document_exists( next):
                self.logger.error('%s is part of %s but does not exist'%( next, crid))
                continue
            mcm_r = request(rdb.get( next ))
            if mcm_r.get_attribute('status')!='new':
                # this cannot be right!
                self.logger.error('%s is after the current request and is not new: %s' %( next, mcm_r.get_attribute('status')))
                return {"results":False, "message":"%s is not new"%(next),"prepid" : crid}

        ##get the one to be reset
        current_id=mcm_cr.get_attribute('chain')[current_step]
        mcm_r = request( rdb.get( current_id ))
        mcm_r.reset()
        saved = rdb.update( mcm_r.json() )
        if not saved:
            {"results":False, "message":"could not save the last request of the chain","prepid" : crid}
        ## the current chained request has very likely been updated : reload it as you have not changed anything to it yet
        mcm_cr = chained_request( crdb.get( crid) )

        mcm_cr.set_attribute('step',current_step -1 )
        # set status, last status
        mcm_cr.set_last_status()
        mcm_cr.set_attribute('status','processing')

        saved = crdb.update( mcm_cr.json())
        if saved:
            return {"results":True,"prepid" : crid}
        else:
            return {"results":False, "message":"could not save chained requests. the DB is going to be inconsistent !","prepid" : crid}
        

class ApproveRequest(RESTResource):
    def __init__(self):
        self.acces_limit = 3 

    def GET(self,  *args):
        """
        move the chained request approval to the next step
        """
        if not args:
            self.logger.error('No arguments were given')
            return dumps({"results":'Error: No arguments were given'})
        if len(args) == 1:
                return dumps(self.multiple_approve(args[0]))
        return dumps(self.multiple_approve(args[0], int(args[1])))

    def multiple_approve(self, rid, val=-1):
        if ',' in rid:
            rlist = rid.rsplit(',')
            res = []
            for r in rlist:
                 res.append(self.approve(r, val))
            return res
        else:
            return self.approve(rid, val)

    def approve(self,  rid,  val=-1):
        db = database('chained_requests')
        if not db.document_exists(rid):
            return {"prepid": rid, "results":'Error: The given chained_request id does not exist.'}
        creq = chained_request(json_input=db.get(rid))
        try:
            creq.approve(val)
        except Exception as ex:
            return {"prepid": rid, "results":False, 'message' : str(ex)} 

        saved = db.update(creq.json())
        if saved:
            return {"prepid":rid, "results":True}
        else:
            return {"prepid":rid, "results":False , 'message': 'unable to save the updated chained request'}


class InspectChain(RESTResource):
    def __init__(self):
        self.acces_limit = 3

    def GET(self, *args):
        """
        Inspect a chained request for next action
        """
        if not args:
            return dumps({"results":'Error: No arguments were given'})
        return dumps(self.multiple_inspect(args[0]))

    def multiple_inspect(self, crid):
        crlist=crid.rsplit(',')
        res = []
        crdb = database('chained_requests')
        for cr in crlist:
            if crdb.document_exists( cr):
                mcm_cr = chained_request( crdb.get( cr) )
                res.append( mcm_cr.inspect() )
            else:
                res.append( {"prepid": cr, "results":False, 'message' : '%s does not exist'% cr})

        if len(res)>1:
            return res
        else:
            return res[0]

class GetConcatenatedHistory(RESTResource):
    def __init__(self):
        self.acces_limit = 1

    def GET(self, *args):
        if not args:
            return dumps({"results": 'Error: No arguments were given'})
        return dumps(self.concatenate_history(args[0]))

    def concatenate_history(self, id_string):
        res = {}
        tmp_history = {}
        crdb = database('chained_requests')
        rdb = database('requests')
        id_list = id_string.split(',')
        for elem in id_list: ##get data for single chain -> save in tmp_hist key as chain_id ???
            tmp_history[elem] = []
            chain_data = crdb.get(elem)
            #/get request and then data!
            for request in chain_data["chain"]:
                request_data = rdb.get(request)
                tmp_data = request_data["history"]
                try:
                    if tmp_data[0]["step"] != "new":  #we set 1st step to new -> so graph would not ignore undefined steps: clone, <flown> step, migrated
                        tmp_data[0]["step"] = "new"
                except:
                    tmp_data[0]["step"] = "new"

                for step in tmp_data:
                    step["request_id"] = request_data["prepid"]
                    tmp_history[elem].append(step)
        return {"results":tmp_history, "key": id_string}

class SearchableChainedRequest(RESTResource):
    def __init__(self):
        self.access_limit = access_rights.user

    def GET(self, *args):
        """
        Return a document containing several usable values that can be searched and the value can be find. /do will trigger reloading of that document from all requests
        """
        rdb = database('chained_requests')
        if len(args) and args[0] == 'do':
            all_requests = rdb.queries([])

            searchable = {}

            for request in all_requests:
                for key in ["prepid", "approval", "status", "pwg", "step",
                            "last_status", "member_of_campaign", "dataset_name"]:
                    if not key in searchable:
                        searchable[key] = set([])
                    if not key in request:
                        ## that should make things break down, and due to schema evolution missed-migration
                        continue
                    if type(request[key]) == list:
                        for item in request[key]:
                            searchable[key].add(str(item))
                    else:
                        searchable[key].add(str(request[key]))

            #unique it
            for key in searchable:
                searchable[key] = list(searchable[key])
                searchable[key].sort()

            #store that value
            search = database('searchable')
            if search.document_exists('chained_requests'):
                search.delete('chained_requests')
            searchable.update({'_id': 'chained_requests'})
            search.save(searchable)
            searchable.pop('_id')
            return dumps(searchable)
        else:
            ## just retrieve that value
            search = database('searchable')
            searchable = search.get('chained_requests')
            searchable.pop('_id')
            searchable.pop('_rev')
            return dumps(searchable)


class TestChainedRequest(RESTResource):
    def __init__(self):
        self.access_limit = access_rights.user
        
    def GET(self, *args):
        """                       
        Perform test for chained requests
        """
        from tools.handlers import ConfigMakerAndUploader
        from tools.locker import locker
        target=8*60*60 ## seconds
        crn= args[0]
        crdb = database('chained_requests')
        ccdb = database('chained_campaigns')
        rdb = database('requests')
        mcm_cr = chained_request(crdb.get(crn))
        mcm_cc = chained_campaign( ccdb.get( mcm_cr.get_attribute('member_of_campaign')))
        ## assume all requests have config_id
        command='wmcontrol.py '
        from tools.locator import locator
        l_type=locator()
        wma={
            "RequestType" : "TaskChain",
            #"DbsUrl" : l_type.cmsweburl()+"dbs/prod/global/DBSReader",
            #"CouchURL" : l_type.cmsweburl()+'couchdb',
            #"ConfigCacheURL" : l_type.cmsweburl()+'couchdb',
            "inputMode" : "couchDB",
            "RequestString" : crn.replace(mcm_cc.get_attribute('prepid'), mcm_cc.get_attribute('alias')),
            "Group" : "ppd",
            "Requestor": "pdmvserv",
            #"Campaign" : mcm_cc.get_attribute('alias'),
            "Campaign" : mcm_cc.get_attribute('prepid'),
            "OpenRunningTimeout" : 43200,
            "TaskChain" : 0,
            "ProcessingVersion": 1,
            }
        mcm_rs=[]
        for rn in mcm_cr.get_attribute('chain'):
            self.logger.log("uploading for"+rn)
            uploader = ConfigMakerAndUploader(prepid=rn, lock = locker.lock(rn))
            uploader.run()
            mcm_rs.append( request( rdb.get( rn )))

        step=1
        last_io=None
        for (i,r) in enumerate( mcm_rs ):

            steps='step%d'%step
            for (si, seq) in enumerate(r.get_attribute('sequences')):
                command+='--%s-docID %s '%( steps, r.get_attribute('config_id')[si] )
                command+='--%s-globaltag %s '%( steps, r.get_attribute('sequences')[si]['conditions'] )
                command+='--%s-release %s '%( steps, r.get_attribute('cmssw_release') )
                if step!=1:
                    command+='--%s-input Task%d '%( steps, step-1 )
                    command+='--%s-input-output %soutput '%( steps, last_io )
                wma["RequestPriority"] = r.get_attribute('priority')
                wma["Memory"] = r.get_attribute('memory')
                wma['Task%d'%step] ={'TaskName' : 'Task%d'%step,
                                     "ConfigCacheID" : r.get_attribute('config_id')[si],
                                     "GlobalTag" : r.get_attribute('sequences')[si]['conditions'],
                                     "CMSSWVersion" : r.get_attribute('cmssw_release'),
                                     "ScramArch": r.get_scram_arch(),
                                     "PrimaryDataset" : r.get_attribute('dataset_name'),
                                     "KeepOutput" : r.get_attribute('keep_output')[si],
                                     "AcquisitionEra" : r.get_attribute('member_of_campaign'),
                                     "ProcessingString" : r.get_processing_string(si),
                                     "ProcessingVersion" : r.get_attribute('version'),
                                     "TimePerEvent" : r.get_attribute("time_event"),
                                     "SizePerEvent" : r.get_attribute('size_event'),
                      }
                if r.get_attribute('pileup_dataset_name'):
                    wma['Task%d'%step]["MCPileup"] = r.get_attribute('pileup_dataset_name')
                for item in ['CMSSWVersion','ScramArch','TimePerEvent','SizePerEvent','GlobalTag']:
                    #wma[item] = wma['Task%d'%step].pop(item)
                    wma[item] = wma['Task%d'%step][item]

                if step==1:
                    nepj = int(target / r.get_attribute('time_event'))
                    if nepj==0:
                        return dumps({"results" : False, "message" : "not possible to split %s for target %s with %s s/event" % ( r.get_attribute('prepid'), target, r.get_attribute('time_event'))})
                    
                    wma['Task%d'%step].update({"SplittingAlgo"  : "EventBased",
                                               "EventsPerJob" : nepj,
                                               "RequestNumEvents" : r.get_attribute('total_events'),
                                               "Seeding" : "AutomaticSeeding", 
                                               })
                else:
                    ##assuming that 100 events per lumi all the time
                    nlpj = int(target / r.get_attribute('time_event') / 100.)
                    if nlpj==0:
                        return dumps({"results" : False, "message" : "not possible to split %s for target %s with %s s/event" % ( r.get_attribute('prepid'), target, r.get_attribute('time_event'))})


                    wma['Task%d'%step].update({"SplittingAlgo"  : "LumiBased",
                                               "LumisPerJob" : nlpj,
                                               "InputFromOutputModule" : "%soutput"%last_io,
                                               "InputTask" : "Task%d"%(step-1)
                                               })
                last_io=r.get_attribute('sequences')[si]['eventcontent'][0]
                wma['TaskChain']+=1
                step+=1
        if len(args)>1:
            if args[1]in ['inject','show']:
                from tools.ssh_executor import ssh_executor
                with ssh_executor(server = 'pdmvserv-test.cern.ch') as ssh:
                    cmd='cd /afs/cern.ch/cms/PPD/PdmV/work/McM/dev-submit/\n'
                    cmd+=mcm_rs[0].make_release()
                    cmd+='export X509_USER_PROXY=/afs/cern.ch/user/p/pdmvserv/private/$HOST/voms_proxy.cert\n'
                    cmd+='export PATH=/afs/cern.ch/cms/PPD/PdmV/tools/wmcontrol:${PATH}\n'
                    cmd+='wmcontrol.py --wmtest --url-dict https://cms-pdmv-dev.cern.ch/mcm/public/restapi/chained_requests/test/%s\n'%(crn)
                    if args[1]=='show':
                        cherrypy.response.headers['Content-Type'] = 'text/plain'
                        return cmd
                    else:
                        _, stdout, stderr = ssh.execute(cmd)
                        cherrypy.response.headers['Content-Type'] = 'text/plain'
                        return stdout.read()+'\n\n-------------\n\n'+stderr.read()
                        #return dumps({"out":stdout.read(),"err":stderr.read()})

        return dumps(wma)


class GetSetupForChains(RESTResource):
    def __init__(self, mode='setup'):
        self.access_limit = access_rights.user
        self.opt = mode
        if self.opt not in ['setup','test','valid']:
            raise Exception("Cannot create this resource with mode %s"% self.opt)
        if self.opt=='valid':
            self.access_limit = access_rights.administrator


    def GET(self, *args, **kwargs):
        if not len(args):
            return dumps({"results": False, "message": "Chained request prepid not given"})
        crdb = database('chained_requests')
        if not crdb.document_exists(args[0]):
            return dumps({"results": False, "message": "Chained request with prepid {0} does not exist".format(args[0])})
        cr = chained_request(crdb.get(args[0]))
        events = None
        run = False
        valid = False
        directory = ''
        if self.opt=='test' or self.opt=='valid':
            run = True
        if self.opt=='valid':
            valid = True

        if 'events' in kwargs:
            events = int(kwargs['events'])
        if 'directory' in kwargs:
            directory = kwargs['directory']

        cherrypy.response.headers['Content-Type'] = 'text/plain'
        return cr.get_setup(directory=directory, run=run, events=events, validation=valid)
