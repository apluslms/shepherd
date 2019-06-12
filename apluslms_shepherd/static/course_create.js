//  This file is for course_create.html


// The section 'div_parent_group' hide and show control
$(function() {
    var checkbox = $("#new_group"); // The checkbox that create a new group
    var div_parent_group = $("#div_parent_group");
    div_parent_group.hide(); // Initially, hiden the parent_group section
    var parent_group = $("#parent_group");
    
    // Setup an event listener for when the state of the 
    // checkbox changes.
    checkbox.change(function() {
    if (checkbox.is(':checked')) {  
        div_parent_group.show();  // Show the parent_group drop-down list 
        parent_group.change(function(){  // If a parent_group is selected
            if (parent_group.val()!=0) {
            $('#createGroupModal').modal();  // Show the CreateGroup modal
            }})}
    else {  // If the checkbox is unchecked, hide the elements
        div_parent_group.hide();
        $("#createGroupModal").modal('hide');
    }
    });
});  
    

// Set the self_admin permission checkbox 
// in the groupCreateModal is checked
$(function(){  
    $("#permissions-self_admin").prop('checked', true);
});
    

// createGroupForm submission
$(function() {
    var form = $('#GroupForm');
    var parent_group = $("#parent_group");
    // Submit the form
    $(form).submit(function(event) {
        var formData = $('#GroupForm').serialize();
            $.ajax({
            // Add the group_id query string to the url
            url:  form.attr('action')+'?group_id='+parent_group.val(),  
            type: 'POST',
            data:  formData,
            success:function(data){  // The new group is created successfully
            // Update 'owner_group' dorpdown list and change its value 
            select = document.getElementById('owner_group');
            var opt = document.createElement('option');
            opt.value = data.group_id;
            opt.innerHTML = data.group_slug;
            select.add(opt);
            $('#owner_group').val(data.group_id);
            // Hide the elements
            $('#createGroupModal').modal('hide');
            $('#div_parent_group').hide();
            $('#div_new_group').hide();
            },
            error: function(){
                alert('Could not create the group');
                }
            });
        // Stop the browser from submitting the form.
        event.preventDefault();
    });   
});      
    