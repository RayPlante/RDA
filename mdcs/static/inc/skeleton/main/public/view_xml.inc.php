<?php
	require_once $_SESSION['config']['_ROOT_'].'/parser/parser.inc.php';
?>
<div id="featured-wrapper"><div id="featured">
	<h1>XML View</h1>
	<p>
		This is a preview of the curated data in XML format. As part of this demo, please save your data to the repository so that we can better evaluate our system. You can also click the download button for a copy on your local machine.
	</p>
</div></div>

<div id="main">
	
	
	<?php
		if(($xmlTree = displayXmlTree()) == null)
		{
	?>
	
	<div class="alert alert-block">
		<p>
			<i class="icon warning"></i>
			<strong>Warning:</strong> You have to select a template to be able to enter data.
			
			<button class="btn btn-small btn-warning pull-right">Select a template</button>
		</p>
	</div>
	
	<?php
		}
		else
		{
	?>
	<div class="message"></div>
	
	<div class="btn-group pull-right">
		<button class="btn download-xml"><i class="icon-arrow-down"></i> Download XML</button>
		<button class="btn save-to-repo"><i class="icon-star"></i> Save to repository</button>
	</div>
	
	<div id="XMLHolder"></div>
	
	<script src="inc/controllers/js/view_xml.js"></script>
	<script>
		LoadXMLString('XMLHolder', <?php echo "'".str_replace('"', '\\"', $xmlTree)."'"; ?>);
		
		loadViewXmlController();
	</script>
	
	<?php
		}
	?>
</div>