
angular.module('testApp').controller('notificator',
  ['$scope', '$http', '$location', '$window',
  function notificator($scope, $http, $location, $window){
    $scope.show_notifications = false;
    $scope.unseen = -1;
    $scope.notification_numbers = {};
    $scope.notifications = {};
    $scope.sorted_groups = [];
    $scope.display_notifications = false;
    $scope.overlay_height = "0%";
    $scope.overlay_title = "";
    $scope.overlay_message = "";
    $scope.search_text = "";
    $scope.searched_notifications = [];
    $scope.search_on = false;
    $scope.search_page = 0;
    $scope.search_items_left = false;
    $scope.group_object = {
      'Batches' : 'batches',
      'Chained_requests' : 'chained_requests',
      'Request_approvals' : 'requests',
      'Request_operations' : 'requests',
      'Requests_in_approved' : 'requests',
      'Requests_in_defined' : 'requests',
      'Requests_in_done' : 'requests',
      'Requests_in_new' : 'requests',
      'Requests_in_submitted' : 'requests',
      'Requests_in_validation' : 'requests',
      'Users' : 'users'
    }

    $scope.checkNotifications = function(){
      var promise = $http.get("restapi/notifications/check");
      promise.then(function(data) {
            $scope.notification_numbers = data.data;
            $scope.unseen = $scope.notification_numbers.unseen;
            delete $scope.notification_numbers.unseen;
            $scope.sorted_groups = Object.keys($scope.notification_numbers).sort();
        }, function() {
            alert("Error checking notifications");
        });
    }

    $scope.fetchSearch = function(){
      var promise = $http.get("restapi/notifications/search?search=" + $scope.search_text.trim() + '&page=' + $scope.search_page);
      promise.then(function(data) {
            $scope.searched_notifications = $scope.searched_notifications.concat(data.data);
            if(data.data.length < 10){
              $scope.search_items_left = false;
            } else{
              $scope.search_items_left = true;
            }
        }, function() {
            alert("Error searching notifications");
        });
    }

    $scope.search = function(){
      if($scope.search_text === '' || !$scope.search_on){
        return;
      }
      $scope.search_page = 0;
      $scope.searched_notifications = [];
      $scope.fetchSearch();
    }


    $scope.continueSearch = function(){
      $scope.search_page += 1;
      $scope.fetchSearch();
    }

    $scope.showActions = function(object_type, notification_id, seen, $event){
      if(!seen){
        $scope.saveSeenNotification(notification_id);
      }
      window.location = object_type + "?from_notification=" + notification_id;
      $event.stopPropagation();
    }

    $scope.showGroup = function(group){
      if($scope.notifications.hasOwnProperty(group)){
        $scope.notifications[group]['is_selected'] = !$scope.notifications[group]['is_selected'];
      } else{
        $scope.fetchNotifications(group);
      }
    }

    $scope.fetchNotifications = function(group){
      var page = $scope.notifications.hasOwnProperty(group) ? $scope.notifications[group].page : 0;
      var groupAux = group == 'All' ? '*' : group
      var promise = $http.get("restapi/notifications/fetch?page=" + page + "&group=" + groupAux);
      promise.then(function(data) {
            if(!$scope.notifications.hasOwnProperty(group)){
              $scope.notifications[group] = {};
              $scope.notifications[group]['page'] = 0;
              $scope.notifications[group]['is_selected'] = true;
              $scope.notifications[group]['more_to_fetch'] = true;
              $scope.notifications[group]["notifications"] = [];
            }
            $scope.notifications[group]["notifications"] = $scope.notifications[group]["notifications"].concat(data.data.notifications);
            $scope.notifications[group]['page'] += 1;
            if (data.data.notifications.length < 10) {
              $scope.notifications[group]['more_to_fetch'] = false;
            }
        }, function() {
            alert("Error fetching notifications");
        });
    }

    $scope.saveSeenNotification = function(notification_id){
      $http({method:'POST', url:"restapi/notifications/seen", data: {"notification_id": notification_id}}).success(function(data,status){
      }).error(function(status){
      });
    }

    $scope.showNotification = function(notification){
      if(!notification.seen){
        notification.seen = true;
        $scope.saveSeenNotification(notification._id);
        if($scope.notifications.hasOwnProperty('All')){
          for(var index in $scope.notifications.All.notifications){
            if($scope.notifications.All.notifications[index]._id == notification._id){
              $scope.notifications.All.notifications[index].seen = true;
            }
          }
        }
        $scope.unseen -= 1;
      }
      $scope.overlay_height = '100%';
      $scope.overlay_message = notification.message;
      $scope.overlay_title = notification.title;
    }

    $scope.showGroupActions = function(group, $event){
      window.location = $scope.group_object[group] + "?from_notification_group=" + group;
      $event.stopPropagation();
    }

    $scope.markGroupAsSeen = function(group, $event){
      group = group == "All" ? "*" : group
      $http({method:'POST', url:"restapi/notifications/mark_as_seen", data: {"group": group}}).success(function(data,status){
        if(data.results){
          alert("Notifications marked as seen")
        } else {
          alert("Error: " + data.message)
        }
      }).error(function(status){
        alert("Error while trying to mark notifications as seen")
      });
      $event.stopPropagation();
    }

    $scope.displayNotifications = function(){
      $scope.display_notifications = !$scope.display_notifications;
      if(!$scope.display_notifications){
        $scope.notifications = {};
      }
    }
    $scope.checkNotifications();
  }
]);