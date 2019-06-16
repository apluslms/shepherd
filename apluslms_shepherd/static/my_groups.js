var old_owner_id = null;

$(function() { // Delete a group and remove it from the group list

    // Trigger the delete event
    $('.delete').click(function(event) {
        var group_id = $(this).val();
        old_owner_id = $(this).val();  // Change the value of old_owner_id for removing courses
        $.ajax({
        // Add the group_id query string to the url
        url: '/groups/delete/'+'?group_id='+group_id,  
        type: 'POST',
        success:function(data){  // The group is deleted successfully
        // Remove the group element
        var group = $('.group[value='+group_id+']');
        alert('The group has been deleted');
        group.remove();
        },
        statusCode: {
            406: function (response) {
                error = JSON.parse(response.responseText)
                alert(error.message);
                $('#moveCourseModal').modal();
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


$(function move_courses() {  

    fetch('/groups/options_of_new_owner/')  // Update the dropdown options of new owner group
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

    $('#move_courses').click(function(event) { // Post the request of moving courses from the old owner
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
});      