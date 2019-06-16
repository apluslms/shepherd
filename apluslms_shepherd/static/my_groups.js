$(function() { // Delete a group and remove it from the group list

    // Trigger the delete event
    $('.delete').click(function(event) {
        var group_id = $(this).val();
        $.ajax({
        // Add the group_id query string to the url
        url: '/groups/delete/'+'?group_id='+group_id,  
        type: 'POST',
        success:function(data){  // The group is deleted successfully

        alert('The group has been deleted');
        // Remove the group element
        var group = $('.group[value='+group_id+']');
        group.remove();
        },
        statusCode: {
            406: function (response) {
                error = JSON.parse(response.responseText)
                alert(error.message);
                $('#moveCourseModal').modal();
                move_courses(group_id);
            },
            501:function (response) {
                error = JSON.parse(response.responseText)
                alert(error.message);
            }}
        });
        // Stop the browser from submitting the form.
        event.preventDefault();
    });   
});      


$(function() {  // Update the dropdown options of new owner group

    fetch('/groups/options_of_new_owner/')  // fetch the groups from the database
    .then(function(response){
        if (response.status !== 200) {  
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
});


function move_courses(old_owner_id) {  // Post the request of moving courses

    var test='/groups/move_course/'+'?old_owner_id='+old_owner_id+'&new_owner_id='+$('#new_owner').val();  
    console.log(test)
    $('#move_courses').click(function(event) {
        $.ajax({
        // Add the group_id query string to the url
        url: '/groups/move_course/'+'?old_owner_id='+old_owner_id+'&new_owner_id='+$('#new_owner').val(),  
        type: 'POST',
        success:function(data){  // The group is deleted successfully
        alert('The courses have been moved');
        $('#moveCourseModal').modal('hide');
        },
        error:function(){
            alert('Failed to move the courses');
        }
        });
        // Stop the browser from submitting the form.
        event.preventDefault();
    });   
};      