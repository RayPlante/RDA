<div id="featured-wrapper"><div id="featured">
	<h1>Schema configuration</h1>
</div></div>

<div id="main">
<div id="schema_prop">
	<div id="main_prop">
		<div class="prop"><span class="fieldname">Filename:</span> test.xsd</div>
	</div>
	<div id="misc_prop">
		<div class="prop"><span class="fieldname">Last modification:</span> 12-04-2012 11:32am</div>
		<div class="prop"><span class="fieldname">Size:</span> 120 Mo</div>
	</div>
</div>
<div id="schema_content">	
	<h3 style="float:left">Elements</h3>
	<div class="right-side">
		<span class="fieldname">Split into</span> <input class="text" type="number" value="1"/> <span class="fieldname">page(s)</span>
		<span class="ctx_menu">
			<div class="icon legend refresh">Reload</div>
			<div class="icon legend save">Save</div>
		</span>
	</div>
	<div id="schema_elements">
		<?php
			require_once $_SESSION['config']['_ROOT_'].'/parser/parser.inc.php';
		
			$schemaFile = $_SESSION['config']['_ROOT_'].'/resources/files/schemas/demo.light.xsd';
			loadSchema($schemaFile);
		
			displayConfiguration();
		?>
	</div>
</div>
</div>

<script src="parser/controllers/js/edit.js"></script>
<script src="resources/js.new/xsd_cfg.js"></script>
<script>
	loadEditController();
	loadXsdConfigHandler();
</script>
