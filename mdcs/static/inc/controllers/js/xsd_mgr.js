/**
 * 
 */
loadXsdManagerHandler = function()
{
    console.log('BEGIN [loadXsdManagerHandler]');
    $('.add').on('click', setCurrentModel);
    $('.delete').on('click', deleteCurrentSchema);
    $('.copy.schema').on('click', copySchema);
    $('.upload.schema').on('click', uploadSchema);
    console.log('END [loadXsdManagerHandler]');
}

/**
 * 
 */
displayModelSelectedDialog = function()
{
 $(function() {
    $( "#dialog-message" ).dialog({
      modal: true,
      buttons: {
        Ok: function() {
          $( this ).dialog( "close" );
        }
      }
    });
  });
}

/**
 * 
 */
setCurrentModel = function()
{
    console.log('BEGIN [setCurrentModel]');
    var modelName = $(this).parent().siblings(':first').text();
    var modelFilename = $(this).parent().siblings(':nth-child(2)').text();
    var tdElement = $(this).parent();
	
    $('.add').off('click');
		
    tdElement.html('<img src="/static/resources/img/ajax-loader.gif" alt="Loading..."/>');
		
    console.log('[setCurrentModel] Loading '+modelName+' with filename '+modelFilename+' as current model...');

    Dajaxice.curate.setCurrentModel(setCurrentModelCallback,{'modelFilename':modelFilename});
	
//    $.ajax({
//        url: 'inc/controllers/php/schemaLoader.php',
//        type: 'GET',
//        success: function(data) {
//        	// Refresh the page
//        	loadPage($(location).attr('href')+'?manageSchemas');
//        	console.log('[setCurrentModel] '+modelName+' loaded');
//        },
//        error: function() {
//            console.error("[setCurrentModel] A problem occured during schema loading");
//        },
//        // Form data
//        data: 'n='+modelName,
//        //Options to tell JQuery not to process data or worry about content-type
//        cache: false,
//        contentType: false,
//        processData: false
//    });

    console.log('END [setCurrentModel]');
}

setCurrentModelCallback = function(data)
{
    Dajax.process(data);
    console.log('BEGIN [setCurrentModelCallback]');
//    location.reload();

//    var messageLocation = $("#main").children(":first");
//    messageLocation.hide().html("Template Successfully Selected").fadeIn(500);
//    messageLocation.delay(2000).fadeOut(500);

    $('#model_selection').load(document.URL +  ' #model_selection', function() {
	loadXsdManagerHandler();
	//displayModelSelectedDialog();
    });
    console.log('END [setCurrentModelCallback]');
}

/**
 * 
 */
deleteCurrentSchema = function()
{
    console.log('BEGIN [deleteCurrentSchema]');

    $(function() {
        $( "#dialog-deleteconfirm-message" ).dialog({
            modal: true,
            buttons: {
		Yes: function() {
                    $( this ).dialog( "close" );
                },
		No: function() {
                    $( this ).dialog( "close" );
                }
	    }
        });
    });
	
    console.log('END [deleteCurrentSchema]');
}

/**
 * 
 */
copySchema = function()
{
    console.log('BEGIN [copySchema]');

    $(function() {
        $( "#dialog-copied-message" ).dialog({
            modal: true,
            buttons: {
		Ok: function() {
                    $( this ).dialog( "close" );
                }
	    }
        });
    });
	
    console.log('END [copySchema]');
}

/**
 * 
 */
uploadSchema = function()
{
    console.log('BEGIN [uploadSchema]');

    $(function() {
        $( "#dialog-upload-message" ).dialog({
            modal: true,
            buttons: {
		Ok: function() {
                    $( this ).dialog( "close" );
                }
	    }
        });
    });
	
    console.log('END [uploadSchema]');
}
