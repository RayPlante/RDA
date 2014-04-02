/**
 *	Website page loader
 */
$(document).ready(function(){
	loadPage($(location).attr('href'));

	$('.submenu').on('click', changePage);
});

/**
 * Function to load the content of a page. It is called after a click on a link
 * @param {String} url
 * @return {String} JSON string with {"html": "htmlCode", "controller": "scriptName"}
 */
loadPage = function(url)
{
	$.ajax({
        url: 'inc/controllers/php/pageLoader.php',
        type: 'GET',
        success: function(data) {
        	// Destroy and remove the dialog to avoid to rewrite on it
        	$( "#dialog" ).dialog("destroy");
        	$( "#dialog" ).remove();

        	$('.content').children().remove();

        	// Change content
        	$('.content').html(data);

        	console.log('[loadPage] '+url+' loaded');
        },
        error: function() {
            console.error("[loadPage] A problem occured during page loading.");
        },
        // Form data
        data: 'url='+url,
        //Options to tell JQuery not to process data or worry about content-type
        cache: false,
        contentType: false,
        processData: false
    });
}

/**
 * Function to laod a submenu page
 */
changePage = function()
{
	// Update the submenu cursor
	$(this).parent().children('.current').attr('class', 'submenu');
	$(this).attr('class', 'submenu current');

	// Load content
	loadPage($(location).attr('href')+'?'+$(this).attr('id'));
}
