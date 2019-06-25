//  This file is for my_groups.html

var old_owner_id = null;


function fetch_owners_option(old_owner_id){

    fetch('/groups/options_of_new_owner/?old_owner_id='+old_owner_id)  // Update the dropdown options of new owner group
    .then(function(response){
        if (response.status !== 200) {  
            alert('Error');
            console.log('Error occurs. Status Code: ' +
                response.status);
            return;}        
        response.json().then(function(data){
            // Update the html of the 'parent_group' element
            $("#new_owner").html('');  // Empty the 'parent_group' option
            for ( group of data.owner_options){  // Add options
                $('#new_owner').append('<option value= ' + group.id + '>' + group.name + '</option>');
            }
        })
    })
}

$(function() { // Delete a group and remove it from the group list
    // Post the delete event
    $('.delete_form').submit(function(event) {
  
    event.preventDefault(); // avoid to execute the actual submit of the form
    
    group_id = $(this).attr('value'); // Change the value of old_owner_id for removing courses
    $.ajax({
    type: 'POST',
    url: $(this).attr('action')+'?return_error=true', 
    success: function () {
    alert('Delete the group successfully');
    location.reload();
    },
    error: function(response){
        console.log(response.status);
        if (response.status==406){
            old_owner_id = group_id;
            error = JSON.parse(response.responseText)
            alert(error.message);
            fetch_owners_option(old_owner_id);
            $('#moveCourseModal').modal();
        }
        else{
            error = JSON.parse(response.responseText)
            alert(error.message);
        }
       }
    });
    }); 
    });


$(function move_courses() {  

    $('#owner_form').submit(function(event) { // Post the request of moving courses from the old owner
        event.preventDefault(); 
        $.ajax({
        // Add the group_id query string to the url
        url: '/groups/move_course/'+'?old_owner_id='+old_owner_id+'&new_owner_id='+$('#new_owner').val(),  
        type: 'POST',
        success:function(){  // The group is deleted successfully
        old_owner_id = null;
        alert('The courses have been moved');
        $('#moveCourseModal').modal('hide');
        },
        error:function(){
            alert('Failed to move the courses');
        }
        });
    });   
});      