from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'materialType', 'modules.registry.views.registry_checkboxes_materialType',
        name='Registry materialType Checkboxes'),
    url(r'structuralMorphology', 'modules.registry.views.registry_checkboxes_structuralMorphology',
        name='Registry structuralMorphology Checkboxes'),
    url(r'propertyClass', 'modules.registry.views.registry_checkboxes_propertyClass',
        name='Registry propertyClass Checkboxes'),
    url(r'experimentalDataAcquisitionMethod', 'modules.registry.views.registry_checkboxes_expAcquisitionMethod',
        name='Registry experimentalDataAcquisitionMethod Checkboxes'),
    url(r'computationalDataAcquisitionMethod', 'modules.registry.views.registry_checkboxes_compAcquisitionMethod',
        name='Registry computationalDataAcquisitionMethod Checkboxes'),
    url(r'sampleProcessing', 'modules.registry.views.registry_checkboxes_sampleProcessing',
        name='Registry sampleProcessing Checkboxes'),
    url(r'status', 'modules.registry.views.status',
        name='Status'),
    url(r'local-id', 'modules.registry.views.localid',
        name='Local ID'),
    url(r'description', 'modules.registry.views.description',
        name='Description'),
    url(r'resource-type', 'modules.registry.views.resource_type',
        name='Resource Type'),
    url(r'name-pid', 'modules.registry.views.name_pid',
        name='Name PID'),
    url(r'fancy_tree_data_origin', 'modules.registry.views.fancy_tree_data_origin',
        name='Fancy Tree Data Origin'),
    url(r'fancy_tree_material_type', 'modules.registry.views.fancy_tree_material_type',
        name='Fancy Tree Material Type'),
    url(r'fancy_tree_structural_feature', 'modules.registry.views.fancy_tree_structural_feature',
        name='Fancy Tree Structural Feature'),
    url(r'fancy_tree_property_addressed', 'modules.registry.views.fancy_tree_property_addressed',
        name='Fancy Tree Property Addressed'),
    url(r'fancy_tree_experimental_method', 'modules.registry.views.fancy_tree_experimental_method',
        name='Fancy Tree Experimental Method'),
    url(r'fancy_tree_characterization_method', 'modules.registry.views.fancy_tree_characterization_method',
        name='Fancy Tree Characterization Method'),
    url(r'fancy_tree_computational_method', 'modules.registry.views.fancy_tree_computational_method',
        name='Fancy Tree Computational Method'),
    url(r'fancy_tree_compute_scale', 'modules.registry.views.fancy_tree_compute_scale',
        name='Fancy Tree Compute Scale'),
    url(r'fancy_tree_synthesis_processing', 'modules.registry.views.fancy_tree_synthesis_processing',
        name='Fancy Tree Synthesis Processing'),
)

