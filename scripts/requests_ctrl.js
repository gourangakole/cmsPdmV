function resultsCtrl($scope, $http, $location, $window){
    $scope.requests_defaults = [
        {text:'PrepId',select:true, db_name:'prepid'},
        {text:'Actions',select:true, db_name:''},
        {text:'Approval',select:true, db_name:'approval'},
        {text:'Status',select:true, db_name:'status'},
        {text:'MCDBId',select:true, db_name:'mcdb_id'},
        {text:'DataSet Name',select:true, db_name:'dataset_name'},
        {text:'SW Release',select:true, db_name:'cmssw_release'},
        {text:'Type',select:true, db_name:'type'},
        {text:'History',select:false, db_name:'history'},
    ];
    $scope.user = {name: "", role:""}
// GET username and role
      var promise = $http.get("restapi/users/get_roles");
       promise.then(function(data){
        $scope.user.name = data.data.username;
        $scope.user.role = data.data.roles[0];
    }, function(data){
        alert("Error getting user information. Error: "+data.status);
    });
// Endo of user info request
    $scope.update = [];
    $scope.show_well = false;
    $scope.chained_campaigns = [];

    if($location.search()["page"] === undefined){
        page = 0;
        $location.search("page", 0);
        $scope.list_page = 0;
    }else{
        page = $location.search()["page"];
        $scope.list_page = parseInt(page);
    }
    $scope.dbName = $location.search()["db_name"];
    
    $scope.delete_object = function(db, value){
        $http({method:'DELETE', url:'restapi/'+db+'/delete/'+value}).success(function(data,status){
            console.log(data,status);
            if (data["results"]){
              $scope.update["success"] = data["results"];
              $scope.update["fail"] = false;
              $scope.update["status_code"] = status;
            }else{
              $scope.update["success"] = false;
              $scope.update["fail"] = true;
              $scope.update["status_code"] = status;
            }
        }).error(function(status){
            alert('Error no.' + status + '. Could not delete object.');
        });
    };
    $scope.single_step = function(step, prepid){
      $http({method:'GET', url: 'restapi/'+$scope.dbName+'/'+step+'/'+prepid}).success(function(data,status){
         $scope.update["success"] = data["results"];
         $scope.update["fail"] = false;
         $scope.update["status_code"] = data["results"];
         $window.location.reload();
      }).error(function(status){
         $scope.update["success"] = false;
         $scope.update["fail"] = true;
         $scope.update["status_code"] = status;
      });
    };
    $scope.next_status = function(prepid){
      $http({method:'GET', url: 'restapi/'+$scope.dbName+'/status/'+prepid}).success(function(data,status){
         $scope.update["success"] = data["results"];
         $scope.update["fail"] = false;
         $scope.update["status_code"] = data["results"];
         $window.location.reload();
      }).error(function(status){
         $scope.update["success"] = false;
         $scope.update["fail"] = true;
         $scope.update["status_code"] = status;
      });
    };
    
    $scope.submit_edit = function(){
        console.log("submit function");
        console.log($scope.result);
        $http({method:'PUT', url:'restapi/'+$location.search()["db_name"]+'/update/',data:JSON.stringify($scope.result[1])}).success(function(data,status){
            console.log(data,status);
            $scope.update["success"] = data["results"];
            $scope.update["fail"] = false;
            $scope.update["status_code"] = status;
	    $window.location.reload();
        }).error(function(data,status){
            $scope.update["success"] = false;
            $scope.update["fail"] = true;
            $scope.update["status_code"] = status;
        });
    };

    $scope.submit = function (prepid){
      $http({method:'GET', url: 'restapi/'+$scope.dbName+'/inject/'+prepid}).success(function(data,status){
         $scope.update["success"] = data["results"];
         $scope.update["fail"] = false;
         $scope.update["status_code"] = data["results"];
	 //         $window.location.reload();
      }).error(function(status){
         $scope.update["success"] = false;
         $scope.update["fail"] = true;
         $scope.update["status_code"] = status;
      });
    };


    $scope.select_all_well = function(){
      $scope.selectedCount = true;
      var selectedCount = 0
      _.each($scope.requests_defaults, function(elem){
        if (elem.select){
          selectedCount +=1;
        }
        elem.select = true;
      });
      if (selectedCount == _.size($scope.requests_defaults)){
      _.each($scope.requests_defaults, function(elem){
        elem.select = false;
      });
      $scope.requests_defaults[0].select = true; //set prepid to be enabled by default
      $scope.requests_defaults[1].select = true; // set actions to be enabled
      $scope.requests_defaults[2].select = true; // set actions to be enabled
      $scope.requests_defaults[3].select = true; // set actions to be enabled
      $scope.requests_defaults[4].select = true; // set actions to be enabled
      $scope.requests_defaults[5].select = true; // set actions to be enabled
      $scope.requests_defaults[6].select = true; // set actions to be enabled
      $scope.requests_defaults[7].select = true; // set actions to be enabled
      $scope.requests_defaults[8].select = true; // set actions to be enabled
      $scope.selectedCount = false;
      }
    };

    $scope.delete_edit = function(id){
        console.log("delete some from edit");
        $scope.delete_object($location.search()["db_name"], id);
    };
    $scope.display_approvals = function(data){
        console.log(data);
    };
       $scope.sort = {
        column: 'prepid',
        descending: false
    };

    $scope.selectedCls = function(column) {
        return column == $scope.sort.column && 'sort-' + $scope.sort.descending;
    };
    
    $scope.changeSorting = function(column) {
        var sort = $scope.sort;
        if (sort.column == column) {
            sort.descending = !sort.descending;
        } else {
            sort.column = column;
            sort.descending = false;
        }
    };
  $scope.showing_well = function(){
        if ($scope.show_well){
          $scope.show_well = false;
        }
        else{
            console.log("true");
            $scope.show_well = true;
        }
    };    

   $scope.$watch('list_page', function(){
      console.log("modified");
      var promise = $http.get("search/?"+ "db_name="+$location.search()["db_name"]+"&query="+$location.search()["query"]+"&page="+$scope.list_page)
          promise.then(function(data){
        $scope.result = data.data.results; 
        if ($scope.result.length != 0){
        columns = _.keys($scope.result[0]);
        rejected = _.reject(columns, function(v){return v[0] == "_";}); //check if charat[0] is _ which is couchDB value to not be shown
         $scope.columns = _.sortBy(rejected, function(v){return v;});  //sort array by ascending order
        _.each(rejected, function(v){
            add = true;
            _.each($scope.requests_defaults, function(column){
            if (column.db_name == v){
                add = false;
            }
         });
            if (add){
                $scope.requests_defaults.push({text:v[0].toUpperCase()+v.substring(1).replace(/\_/g,' '), select:false, db_name:v});
            }
        });
        }
        console.log($scope.requests_defaults);
         }, function(){
             console.log("Error"); 
         });
    });
    
  $scope.previous_page = function(current_page){
      if (current_page >-1){
        $location.search("page", current_page-1);
        $scope.list_page = current_page-1;
      }
  };
  $scope.next_page = function(current_page){
      if ($scope.result.length !=0){
        $location.search("page", current_page+1);
        $scope.list_page = current_page+1;
      }
  };
  $scope.showapproval = false;
  $scope.showApprovals = function(){
      console.log("Approvals click");
      if ($scope.showapproval){
          $scope.showapproval = false;
    }
    else{
        $scope.showapproval = true;
    }
  };
  $scope.selected_prepids = [];
  $scope.add_to_selected_list = function(prepid){
    if (_.contains($scope.selected_prepids, prepid)){
        $scope.selected_prepids = _.without($scope.selected_prepids,prepid)
    }else
        $scope.selected_prepids.push(prepid);
  };
  $scope.next_approval = function(){
    console.log("to be approved:", $scope.selected_prepids.join());
    $http({method:'GET', url:'restapi/'+$scope.dbName+'/approve/'+$scope.selected_prepids.join()}).success(function(data,status){
            alert("Success!");
	    $window.location.reload();
        }).error(function(data,status){
            console.log(status);
            alert("Error while processing request. Code: "+status);
        });
  };
  $scope.previous_approval = function(){
    $http({method:'GET', url:'restapi/'+$scope.dbName+'/reset/'+$scope.selected_prepids.join()}).success(function(data,status){
            alert("Success!");
	    $window.location.reload();
        }).error(function(data,status){
            console.log(status);
            alert("Error while processing request. Code: "+status);
        });
  };
  $scope.status_toggle = function(){
    $http({method:'GET', url:'restapi/'+$scope.dbName+'/status/'+$scope.selected_prepids.join()}).success(function(data,status){
            alert("Success!");
	    $window.location.reload();
        }).error(function(data,status){
            console.log(status);
            alert("Error while processing request. Code: "+status);
        });
  };
  $scope.submit_many = function(){
    _.each($scope.selected_prepids, function(elem){
      $window.open("injectAndLog?prepid="+elem);
    });
    // $http({method:'GET', url:'restapi/'+$scope.dbName+'/inject/'+$scope.selected_prepids.join()}).success(function(data,status){
    //         alert("Success!");
	   //  $window.location.reload();
    //     }).error(function(data,status){
    //         console.log(status);
    //         alert("Error while processing request. Code: "+status);
    //     });
  };
}

// NEW for directive
var testApp = angular.module('testApp', []).config(function($locationProvider){$locationProvider.html5Mode(true);});
testApp.directive("customApproval", function(){
    return{
        require: 'ngModel',
        template:
        '<div>'+
        '  <div ng-hide="display_table">'+
        '    <input type="button" value="Show" ng-click="display_approval()">'+
        '    {{whatever.length}} step(-s)'+
        '  </div>'+
        '  <div ng-show="display_table">'+
        '    <input type="button" value="Hide" ng-click="display_approval()">'+
        '    {{whatever.length}} step(-s)'+
        '    <table class="table table-bordered" style="margin-bottom: 0px;">'+
        '      <thead>'+
        '        <tr>'+
        '          <th style="padding: 0px;">Index</th>'+
        '          <th style="padding: 0px;">Approver</th>'+
        '          <th style="padding: 0px;">Step</th>'+
        '        </tr>'+
        '      </thead>'+
        '      <tbody>'+
        '        <tr ng-repeat="elem in approval">'+
        '          <td style="padding: 0px;">{{elem.index}}</td>'+
        '          <td style="padding: 0px;">{{elem.approver}}</td>'+
        '          <td style="padding: 0px;">{{elem.approval_step}}</td>'+
        '        <tr>'+
        '      </tbody>'+
        '    </table>'+
        '  </div>'+
        '</div>',
        link: function(scope, element, attrs, ctrl){
            ctrl.$render = function(){
                scope.whatever = ctrl.$viewValue;
            };
            scope.display_table= false;
            scope.approval = {};
            scope.display_approval = function(){
                if (scope.display_table){
                    scope.display_table = false;
                }else{
                  scope.display_table = true;
                  console.log(ctrl.$viewValue);
                  scope.approval = ctrl.$viewValue;
                }
            console.log(scope.display_table);
            };
        }
    }
});
testApp.directive("customHistory", function(){
  return {
    require: 'ngModel',
    template: 
    '<div>'+
    '  <div ng-hide="show_history">'+
    '    <input type="button" value="Show" ng-click="show_history=true;">'+
    '  </div>'+
    '  <div ng-show="show_history">'+
    '    <input type="button" value="Hide" ng-click="show_history=false;">'+
    '    <table class="table table-bordered" style="margin-bottom: 0px;">'+
    '      <thead>'+
    '        <tr>'+
    '          <th style="padding: 0px;">Action</th>'+
//     '          <th style="padding: 0px;">Message</th>'+
    '          <th style="padding: 0px;">Date</th>'+
    '          <th style="padding: 0px;">User</th>'+
    '        </tr>'+
    '      </thead>'+
    '      <tbody>'+
    '        <tr ng-repeat="elem in show_info">'+
    '          <td style="padding: 0px;">{{elem.action}}</td>'+
//     '          <td style="padding: 0px;"><a rel="tooltip" title={{elem.message}}><i class="icon-info-sign"></i></a></td>'+
    '          <td style="padding: 0px;">{{elem.updater.submission_date}}</td>'+
    '          <td style="padding: 0px;">'+
    '              <div ng-switch="elem.updater.author_name">'+
    '                <div ng-switch-when="">{{elem.updater.author_username}}</div>'+
    '                <div ng-switch-default>{{elem.updater.author_name}}</div>'+
    '              </div>'+
    '          </td>'+
    '        </tr>'+
    '      </tbody>'+
    '    </table>'+
    '  </div>'+
    '</div>'+
    '',
    link: function(scope, element, attrs, ctrl){
      ctrl.$render = function(){
        scope.show_history = false;
        scope.show_info = ctrl.$viewValue;
      };
    }
  }
});
testApp.directive("sequenceDisplay", function($http){
  return {
    require: 'ngModel',
    template:
    '<div>'+
    '  <div ng-hide="show_sequence">'+
    '    <a rel="tooltip" title="Show" ng-click="getCmsDriver();show_sequence=true;">'+
    '     <i class="icon-eye-open"></i>'+
    '    </a>'+
	//    '    <input type="button" value="Show" ng-click="getCmsDriver();show_sequence=true;">'+
    '  </div>'+
    '  <div ng-show="show_sequence">'+
	//    '    <input type="button" value="Hide" ng-click="show_sequence=false;">'+
    '    <a rel="tooltip" title="Hide" ng-click="show_sequence=false;">'+
    '     <i class="icon-remove"></i>'+
    '    </a>'+
    '    <a rel="tooltip" title="Reset" ng-click="resetCmsDriver();">'+
    '     <i class="icon-repeat"></i>'+
    '    </a>'+
    '    <a rel="tooltip" title="Cast" ng-click="castCmsDriver()">'+
    '     <i class="icon-share"></i>'+
    '    </a>'+
    '    <ul>'+
    '      <li ng-repeat="sequence in driver">{{sequence}}</li>'+
    '    </ul>'+
    '  </div>'+
    '</div>',
    link: function(scope, element, attrs, ctrl){
      ctrl.$render = function(){
        scope.show_sequence = false;
        scope.sequencePrepId = ctrl.$viewValue;
//         scope.sequencePrepId = scope.dbName;
      };
      scope.genericCmsDriver = function(extra){
        if (scope.driver ===undefined || extra!=""){
          var promise = $http.get("restapi/"+scope.dbName+"/get_cmsDrivers/"+scope.sequencePrepId+extra);
          promise.then(function(data){
            scope.driver = data.data.results;
          }, function(data){
             alert("Error: ", data.status);
        });
	}
      };
      scope.getCmsDriver = function(){	  scope.genericCmsDriver("");      };
      scope.resetCmsDriver = function(){	  scope.genericCmsDriver("/-1");      };
      scope.castCmsDriver = function(){	  scope.genericCmsDriver("/1");      };
   }
  }
});