//  This file is for owner_groups.html

var course_key = null;
var instance_key = null;


function list_owners(course_key,instance_key){
    $('#owner_table tbody tr').remove();  // Empty the table
    fetch('/courses/'+course_key+'/'+instance_key+'/owners/')  // fetch the groups from the database
        .then(function(response){
            if (response.status !== 200) {  
                console.log('Error occurs. Status Code: ' +
                    response.status);
                return;}        
            response.json().then(function(data){
                // Update the table
                for ( group of data.owner_groups){  // Add options
                    $('#owner_table').append("<tr>"+
                                            "<td>"+group.name+"</td>"+
                                            "<td>"+"</td>"+
                                            "<td>"+  
                                            "<form class='del_owner_form'>"+
                                            "<button type='submit' name='del_owner_btn' class='btn btn-primary' value="+ group.id+
                                            ">Remove</button>"+
                                            "</form>"+ 
                                            "</td>"+"</tr>");
                }
            })
        });
};


function add_owner_options(course_key,instance_key){
    $.ajax({
        type: 'GET',
        url: '/courses/'+course_key+'/'+instance_key+'/add_owners/options/',
        dataType: 'JSON',
        success: function (data) {
        console.log(data.owner_options);
        $("#owner_add").html('<option disabled="disabled" selected="selected">Please Select</option>');  // Empty the 'parent_group' option
            for ( group of data.owner_options){  // Add options
                $('#owner_add').append('<option value= ' + group.id + '>' + group.name + '</option>');
            }
        },
        error: function(response){
            alert('You can not manage it');
        }
        });
};


(function(){
    
    $('.owner_groups').click(function(){
        course_key = $(this).attr('data-course');
        instance_key =  $(this).attr('data-instance');
        console.log(course_key, instance_key);
        list_owners(course_key,instance_key);
        add_owner_options(course_key,instance_key);
        $('#Modal').modal();
    });
})();


$('#Modal').on('hidden.bs.modal', function () {
    course_key = null;
    instance_key = null;
  })

  
$(".tabbable").tabs();
$('#tabs').on("click", "li", function (event) {    
    if ($(this).attr('id')=='list_li'){
        list_owners(course_key,instance_key);
    }
    if ($(this).attr('id')=='manage_li'){
        add_owner_options(course_key,instance_key);
    }
});


$(document).on("submit", "form.add_owner_form", function(event){
    event.preventDefault();
    // var row = $(this).parents('tr');
     if (confirm("Confirm to add this owner group?")){
        var group_id = $(this).find("#owner_add").val();
        var owner_type =  $(this).find("#owner_type").val();
        $.ajax({
            type: 'POST',
            url: "/courses/"+course_key+"/"+instance_key+"/owners/add/"+'?group_id='+group_id+'&owner_type='+owner_type+'&return_error=true',
            success: function () {
            alert('Add this owner group successfully');
            add_owner_options(course_key,instance_key);
            },
            error: function(response){
                    error = JSON.parse(response.responseText)
                    alert(error.message);
            }
            });
    }
});


$(document).on("submit", "form.del_owner_form", function(event){
    event.preventDefault();
    var row = $(this).parents('tr');
     if (confirm("Confirm to delete this owner group?")){
         var group_id = $(this).find("button[name='del_owner_btn']").val();
         
        $.ajax({
            type: 'POST',
            url: "/courses/"+course_key+"/"+instance_key+"/owners/remove/"+'?group_id='+group_id+'&owner_type='+owner_type+'&return_error=true',
            success: function () {
            alert('Remove this owner group successfully');
            row.remove();
            },
            error: function(response){
                    console.log(response)
                    error = JSON.parse(response.responseText)
                    alert(error.message);
            }
            });
    }
});



