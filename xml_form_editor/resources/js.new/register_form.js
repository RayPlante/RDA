/**
 * 
 */
loadRegisterFormController = function()
{
	$(document).on('keyup', saveFields);
	
	$('.blank').on('click', clearFields);
	$('.save').on('click', saveFields);
}

clearFields = function()
{
	console.log("[clearFields] Clearing fields");

	var inputs = $('input.text');
	
	inputs.each(function()
	{
		var inputId = $(this).parent().attr('id');
		
		if(!isNaN(parseInt(inputId)))
		{
			$(this).attr('value', '');
		}	
	});
	
	$.ajax({
        url: 'inc/ajax.new/manageData.php',
        type: 'GET',
        success: function(data) {
        	
        },
        error: function() {
            console.error("[clearFields] Problem with the AJAX call");
        },
        // Form data
        data: 'a=c',
        //Options to tell JQuery not to process data or worry about content-type
        cache: false,
        contentType: false,
        processData: false
    });

	console.log("[clearFields] Fields cleared");
}

saveFields = function()
{
	console.log("[saveFields] Saving fields...");
	
	var inputs = $('input.text'),
		qString = '';
	
	inputs.each(function()
	{
		var inputId = $(this).parent().attr('id'),
			inputValue = $(this).attr('value');
		
		if(inputValue != '' && !isNaN(parseInt(inputId)))
		{
			console.log('Id '+parseInt(inputId)+' = '+inputValue);
			qString += parseInt(inputId)+'='+inputValue+'&';
		}	
	});
	
	qString = qString.substring(0, qString.length-1);
	
	$.ajax({
        url: 'inc/ajax.new/manageData.php',
        type: 'GET',
        success: function(data) {
        	
        },
        error: function() {
            console.error("[saveFields] Problem with the AJAX call");
        },
        // Form data
        data: 'a=s&'+qString,
        //Options to tell JQuery not to process data or worry about content-type
        cache: false,
        contentType: false,
        processData: false
    });
	
	console.log('qString = '+qString);
}

