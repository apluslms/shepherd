//  This file is for course_create.html


// The 'create_group' modal hide and show control
$(function() {
    var button = $("#new_group"); // The button that create a new group
    
    // Setup an event listener for when the state of the 
    // checkbox changes.
    button.click(function() {
        // Set the self_admin permission checkbox is default checked 
        // in the groupCreateModal
        $("#permissions-self_admin").prop('checked', true);
        $('#createGroupModal').modal();  // Show the CreateGroup modal
    });
});  

    
// Update the possible parent groups of the new course group
// when the identity changes
$(function(){  
    // Init
    var $identity = $("#identity");
    if ($identity.val() !== -1){
        fetch('/groups/perm/' + $identity.val() + '/parents/')  // fetch the groups from the database
        .then(function(response){
            if (response.status !== 200) {  
                console.log('Error occurs. Status Code: ' +
                    response.status);
                return;}        
            response.json().then(function(data){
                // Update the html of the 'parent_group' element
                var $parent_group = $("#parent_group");
                $parent_group.html('');  // Empty the 'parent_group' option
                // var optionHTML = '';
                for ( group of data.parent_options){  // Add options
                    $parent_group.append('<option value= ' + group.id + '>' + group.name + '</option>');
                }
            })
        })
    };
    // Onchange event
    $identity.change(function(){

        fetch('/groups/perm/'+$(this).val()+'/parents/')  // fetch the groups from the database
        .then(function(response){
            if (response.status !== 200) {  
                console.log('Error occurs. Status Code: ' +
                    response.status);
                return;}        
            response.json().then(function(data){
                // Update the html of the 'parent_group' element
                var $parent_group = $("#parent_group");
                $parent_group.html('');  // Empty the 'parent_group' option
                // var optionHTML = '';
                for ( group of data.parent_options){  // Add options

                    // var option = new Option(group.name, group.id); 
                    // $('#parent_group').append($(option));
                    $parent_group.append('<option value= ' + group.id + '>' + group.name + '</option>');
                    // optionHTML += '<option value= ' + group.id + '>' + group.name + '</option>';
                }
                // $("#parent_group").html(optionHTML);
            })
        })
    });
});

// createGroupForm submission
$(function() {
    var form = $('#group_form');
    var parent_group = $("#parent_group");
    // Submit the form
    $(form).submit(function(event) {
        event.preventDefault();  // Stop the browser from submitting the form

        var formData = form.serialize();
        console.log(formData);
        $.ajax({
        type: 'POST',
        // Add the group_id query string to the url
        url: '/groups/course_group/create/'+'?group_id='+parent_group.val(),
        data:  formData,
        success:function(data){  // The new group is created successfully
        // Update 'owner_group' dorpdown list 
        alert('New group is added successfully');
        var select = document.getElementById('owner_group');
        var opt = document.createElement('option');
        opt.value = data.group_id;
        opt.innerHTML = data.group_slug;
        select.add(opt);
        // Set the selected value
        select.value = data.group_id;
        // Hide the elements
        $('#createGroupModal').modal('hide');
        },
        error: function(){
            alert('Could not create the group');
            }
        });
    });   
});      