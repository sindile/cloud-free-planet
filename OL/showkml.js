function init(kmlPath, kmlName, assignmentId, tryNum, resultsAccepted, mapPath, workerId) {

    var saveStrategyActive = false;
    var workerFeedback = false;
    // If this is a mapping HIT or training map, let user save changes.
    if (assignmentId.length > 0) {
        saveStrategyActive = true;
    // Else, check if this is a worker feedback map.
    } else if (workerId.length > 0) {
        workerFeedback = true;
    }

    //
    // *** Create map, overlays, and view ***
    //
    var map = new ol.Map({
        controls: ol.control.defaults({
            attributionOptions:  ({
                collapsible: false
            })
        }).extend([new ol.control.MousePosition({
            coordinateFormat: ol.coordinate.createStringXY(3),
            projection: 'EPSG:4326',
            undefinedHTML: '&nbsp;'
        })]),
        interactions: ol.interaction.defaults({
            doubleClickZoom :false
        }),
        layers: [
            // Create overlay layer(s) group.
            new ol.layer.Group({
                title: 'Overlay(s)',
                layers: []
            }),
            // Create multi-band image layer group.
            //new ol.layer.Group({
            //    title: 'Satellite Image Overlays',
            //    layers: []
            //}),
            // Create base layer group.
            new ol.layer.Group({
                title: 'Base Layer',
                //layers: [dg3Layer, dg2Layer, dg1Layer, planetLayer, mapboxLayer, bingLayer]
                layers: [dg1Layer, mapboxLayer, bingLayer]
            })
        ],
        // Use the specified DOM element
        target: document.getElementById('kml_display')
    });
    // Set view and zoom.
    map.setView(new ol.View({
        projection: 'EPSG:4326',
        center: [0,0],
        zoom: 14,
        minZoom: 4,
        maxZoom: 19
    }));
    
    // *** Create grid cell ***
    // White bounding box KML layer: URL defined in configuration table.
    var kmlUrl = eval(`\`${kmlPath}\``);
    var kmlLayer = new ol.layer.Vector({
        source: new ol.source.Vector({
            url: kmlUrl,
            format: new ol.format.KML({extractStyles: false})
        }),
        style: new ol.style.Style({
            fill: new ol.style.Fill({
                color: 'rgba(255, 255, 255, 0.0)'
            }),
            stroke: new ol.style.Stroke({
                color: 'rgba(255, 255, 255, 1.0)',
                width: 2
            })
        })
    });
    // KML must be fully loaded before getting extent info
    var kmlSource = kmlLayer.getSource();
    var key = kmlSource.on('change', function(e){
        if (kmlSource.getState() === 'ready') {
            kmlSource.unByKey(key);
            var extent = kmlSource.getExtent();
            // Center map around KML
            map.getView().fit(extent, map.getSize());
        }   
    });
    kmlLayer.setMap(map);

    // *** If not a worker feedback case, add mapped fields and WMS layers ***
    if (!workerFeedback) {
        // Add special id for all drawn features for dragging purposes.
        var workerMap = new ol.Collection();
        workerMap.on('add', function(event){
            var feature = event.element;
            feature.set('id', 'worker-map');
        }); 
        var fieldsLayer = new ol.layer.Vector({
            title: "Mapped Fields",
            source: new ol.source.Vector({
                features: workerMap
            }),
            style: new ol.style.Style({
                fill: new ol.style.Fill({
                    // Edit line below to change unselected shapes' transparency.
                    color: 'rgba(255, 255, 255, 0.2)'
                }),
                stroke: new ol.style.Stroke({
                    color: '#ffcc33',
                    width: 2
                }),
                image: new ol.style.Circle({
                    radius: 7,
                    fill: new ol.style.Fill({
                        color: '#ffcc33'
                    })
                })
            })
        });
        fieldsLayer.setMap(map);
        
        //
        //*** Create the WMS layer ***
        //
        //var wmsLayer = new ol.layer.Image({
        //    source: new ol.source.ImageWMS({
        //        url: geoserverUrl,
        //        params: {
        //            layers: 'MappingAfrica:' + image_name,
        //            styles: 'true_color'
        //        },
        //        serverType: 'geoserver'
        //    });
        //});    
        //wmsLayer.setMap(map);

        //map.getLayers().getArray()[0].getLayers().push(wmsLayer);
        map.getLayers().getArray()[0].getLayers().push(fieldsLayer);

        // Add drag interaction (for non-worker feedback cases).
        var dragFeature = null;
        var dragCoordinate = null;
        var dragCursor = 'pointer';
        var dragPrevCursor = null;

        var dragInteraction = new ol.interaction.Pointer({
            handleDownEvent : function(event){
                var feature = map.forEachFeatureAtPixel(event.pixel,    
                    function(feature, layer) {
                        return feature;
                    }
                );
                if(feature && feature.get('id') === 'worker-map') {
                    dragCoordinate = event.coordinate;
                    dragFeature = feature;
                    return true;
                }
                return false;
            },
            handleDragEvent : function(event){
                var deltaX = event.coordinate[0] - dragCoordinate[0];
                var deltaY = event.coordinate[1] - dragCoordinate[1];
                var geometry = dragFeature.getGeometry();
                geometry.translate(deltaX, deltaY);
                dragCoordinate[0] = event.coordinate[0];
                dragCoordinate[1] = event.coordinate[1];
            },
            handleMoveEvent : function(event){
                if (dragCursor) {
                    var map = event.map;
                    var feature = map.forEachFeatureAtPixel(event.pixel,
                        function(feature, layer) {
                          return feature;
                        });
                    var element = event.map.getTargetElement();
                    if (feature) {
                        if (element.style.cursor != dragCursor) {
                            dragPrevCursor = element.style.cursor;
                            element.style.cursor = dragCursor;
                        }
                    } else if (dragPrevCursor !== undefined) {
                        element.style.cursor = dragPrevCursor;
                        dragPrevCursor = undefined;
                    }
                }
            },
            handleUpEvent : function(event){
                dragCoordinate = null;
                dragFeature = null;
                return false;
            }
        });
        map.addInteraction(dragInteraction);
     
    // Else, create reference map and worker map layers
    } else {
        var rMapLayer = new ol.layer.Vector({
            title: "Reference Map",
            source: new ol.source.Vector({
                url: mapPath + '/' + workerId + '/' + kmlName + '_r.kml',
                format: new ol.format.KML({extractStyles: false})
                // Replace with the next 2 lines if we switch to GeoJSON.
                //url: mapPath + '/' + workerId + '/' + kmlName + '_r.json',
                //format: new ol.format.GeoJSON()
            }),
            style: new ol.style.Style({
                fill: new ol.style.Fill({
                    color: 'rgba(255, 204, 51, 0.4)'
                }),
                stroke: new ol.style.Stroke({
                    color: '#ffcc33',
                    width: 2
                }),
            })
        });
        rMapLayer.setMap(map);

        //rMapLayer.getSource().on('change', function (event) {
        //    var source = event.target;
        //    if (source.getState() === 'ready') {
        //        var rfeatures = source.getFeatures();
        //        console.log(rfeatures);
        //        for (var rfeature in rfeatures) {
        //            console.log(rfeatures[rfeature].get('category'));
        //            console.log(rfeatures[rfeature].get('categ_comment'));
        //        }
        //    }
        //});

        var wMapLayer = new ol.layer.Vector({
            title: "Worker Map",
            source: new ol.source.Vector({
                url: mapPath + '/' + workerId + '/' + kmlName + '_w.kml',
                format: new ol.format.KML({extractStyles: false})
                //url: mapPath + '/' + workerId + '/' + kmlName + '_w.json',
                //format: new ol.format.GeoJSON()
            }),
            style: new ol.style.Style({
                fill: new ol.style.Fill({
                    color: 'rgba(0, 0, 255, 0.2)'
                }),
                stroke: new ol.style.Stroke({
                    color: '#0000ff',
                    width: 2
                })
            })
        });
        wMapLayer.setMap(map);

        map.getLayers().getArray()[0].getLayers().push(wMapLayer);
        map.getLayers().getArray()[0].getLayers().push(rMapLayer);
    }

    // *** Add miscellaneous controls ***
    //
    // Zoom control
    var zoomSlider = new ol.control.ZoomSlider();
    map.addControl(zoomSlider);

    // Scale line
    var scaleLine = new ol.control.ScaleLine();
    map.addControl(scaleLine);
    
    // Layer Switcher control
    if (!workerFeedback) {
        showPanel = false;
    } else {
        showPanel = true;
    }
    var layerSwitcher = new ol.control.LayerSwitcher({
        showPanel: showPanel,
        tipLabel: 'Layer Switcher'
    });
    map.addControl(layerSwitcher);

    // Main control bar with sub-menus
    if (!workerFeedback) {
        var retVals = addControlBar(fieldsLayer, workerMap, checkSaveStrategy, checkReturnStrategy, kmlName);
        var mainbar = retVals[0];
        var selectButton = retVals[1];
        map.addControl(mainbar);

    // Worker feedback field selection.
    } else{
        selectFeedback = new ol.interaction.Select({
            condition: ol.events.condition.click,
            layers: [wMapLayer, rMapLayer]
        })
        map.addInteraction(selectFeedback);

        // Adjust labeling block so fields are read-only and save button is invisible.
        document.getElementById("categLabel").setAttribute("disabled", true);
        document.getElementById("commentLabel").setAttribute("readonly", true);
        document.getElementById("labelDone").style.display = "none";
    }

    // *** Handle the labeling block ***
    // Mapping cases.
    if (!workerFeedback) {
        // Add event handler to execute each time a shape is drawn.
        var mainbarVisible = true;
        fieldsLayer.getSource().on('addfeature', function(event) {
            // Render the control bar invisible and inactive.
            mainbar.setVisible(false);
            mainbar.setActive(false);
            mainbarVisible = false;
            // Clear all shape selections.
            selectButton.getInteraction().getFeatures().clear();
            // Display the labeling block.
            showLabelBlock(event.feature);
        });
        // Add event handler to execute each time a shape is selected.
        selectButton.getInteraction().getFeatures().on('add', function (event) {
            // Display the labeling block, but only if a single feature is selected.
            if (selectButton.getInteraction().getFeatures().getLength() == 1) {
                showLabelBlock(event.element);
            } else {
                // Hide the labeling block, in case visible.
                document.getElementById("labelBlock").style.display = "none";
            }
        });
        // Add event handler to execute each time a shape is unselected.
        selectButton.getInteraction().getFeatures().on('remove', function (event) {
            // Hide the labeling block, in case visible.
            document.getElementById("labelBlock").style.display = "none";
        });
    // Worker feedback case.
    } else {
        // Add event handler to execute each time a shape is selected.
        selectFeedback.getFeatures().on('add', function(event) {
            // Ensure that only one layer is enabled.
            if (rMapLayer.getVisible() && wMapLayer.getVisible()) {
                // Clear all shape selections.
                selectFeedback.getFeatures().clear();
                // Hide the labeling block, in case visible.
                document.getElementById("labelBlock").style.display = "none";
                // setTimeout() allows the background tasks above to complete in the 1 second allowed.
                setTimeout("alert('Please deselect the Reference Map or the Worker Map so that your click uniquely identifies a field on a specific layer.');", 1);
            // Display the labeling block, but only if a single feature is selected.
            } else {
                if (selectFeedback.getFeatures().getLength() == 1) {
                    showLabelBlock(event.element);
                } else {
                    // Hide the labeling block, in case visible.
                    document.getElementById("labelBlock").style.display = "none";
                }
            }
        });
        // Add event handler to execute each time a shape is unselected.
        selectFeedback.getFeatures().on('remove', function (event) {
            // Hide the labeling block, in case visible.
            document.getElementById("labelBlock").style.display = "none";
        });
    }
    // Display the label block for the specified feature.
    var curFeature;
    function showLabelBlock(feature) {
        // Get the pixel coordinates of the center of the feature.
        curFeature = feature;
        var extent = feature.getGeometry().getExtent();
        var coords = ol.extent.getCenter(extent);
        var pixel = map.getPixelFromCoordinate(coords);

        // Position the labeling block at this location, and make it visible.
        var style = document.getElementById("labelBlock").style;
        style.left = Math.round(pixel[0]) + "px";
        style.top = (Math.round(pixel[1])) + "px";

        // Set the category and categComment values.
        category = feature.get('category');
        // If attributes are present in the feature, use them.
        if (category !== undefined) {
            categComment = feature.get('categ_comment');
            document.getElementById("categLabel").value = category;
            document.getElementById("commentLabel").value = categComment;
        // Else, initialize the input elements.
        } else {
            // Use select default for normal case, empty selection for worker feedback case.
            if (!workerFeedback) {
                document.getElementById("categLabel").selectedIndex = 0;
            } else {
                document.getElementById("categLabel").value = "";
            }
            document.getElementById("commentLabel").value = "";
        }
        // Display the labeling block.
        style.display = "block";
    };
    // Add event handler to process post-drawing labeling.
    $(document).on("click", "button#labelDone", function() {
        var category = document.getElementById("categLabel").value;
        curFeature.set('category', category);
        var comment = document.getElementById("commentLabel").value;
        curFeature.set('categ_comment', comment);

        // Clear all shape selections.
        selectButton.getInteraction().getFeatures().clear();

        // Hide the labeling block.
        document.getElementById("labelBlock").style.display = "none";

        // Render the control bar active and visible if needed.
        if (!mainbarVisible) {
            mainbarVisible = true;
            mainbar.setActive(true);
            mainbar.setVisible(true);
        }
    });

    // Training case only.
    if (tryNum > 0) {
        if (resultsAccepted == 1) {
            alert("Congratulations! You successfully mapped the crop fields in this map. Please click OK to work on the next training map.");
        } else if (resultsAccepted == 2) {
            alert("We're sorry, but you failed to correctly map the crop fields in this map. Please click OK to try again.");
        }
    }
    // Mapping HIT or training map cases.
    if (resultsAccepted == 3) {
        alert("Error! Through no fault of your own, your work could not be saved. Please try the same map again. We apologize for the inconvenience.");
    }

    function checkSaveStrategy(kmlName) {
        var msg;

        // Check if the Save button is enabled.
        if (!saveStrategyActive) {
            return;
        }
        var features = fieldsLayer.getSource().getFeatures();
        if (features != '') {
            msg = 'You can only save your mapped fields ONCE!\nPlease confirm that you\'re COMPLETELY done mapping fields.\nIf not done, click Cancel.';
        } else {
            msg = 'You have not mapped any fields!\nYou can only save your mapped fields ONCE!\nPlease confirm that you\'re COMPLETELY done mapping fields.\nIf not done, click Cancel.'
        }
        if (!confirm(msg)) {
            return;
        }
        // Don't allow Save button to be used again.
        saveStrategyActive = false

        // Save the current polygons if there are any.
        // NOTE: the KML writeFeatures() function does not support extended attributes.
        // So we need to extract them from each feature and pass them separately as arrays.
        if (features != '') {
            categories = [];
            categComments = [];
            var i = 1;
            for (var feature in features) {
                features[feature].set('name', kmlName + '_' + i);
                categories.push(features[feature].get('category'));
                //console.log("category: " + categories[i-1]);
                categComments.push(features[feature].get('categ_comment'));
                //console.log("categ_comment: " + categComments[i-1]);
                i = i + 1;
            }
            var kmlFormat = new ol.format.KML();
            var kmlData = kmlFormat.writeFeatures(features, {featureProjection: 'EPSG:4326', dataProjection: 'EPSG:4326'});
            // Save the kmlData in the HTML mappingform.
            document.mappingform.kmlData.value = kmlData;
            document.mappingform.categories.value = categories;
            document.mappingform.categComments.value = categComments;
        }
        // Mark that we saved our results.
        document.mappingform.savedMaps.value = true;

        document.mappingform.submit();
    }

    function checkReturnStrategy(kmlName) {
        var msg;

        // Check if the Return button is enabled.
        if (!saveStrategyActive) {
            return;
        }
        msg = 'You are about to return this map without saving any results!\nPlease confirm that this is what you want to do.\nNOTE: this may result in a reduction of your quality score.\nIf you do not wish to return this map, click Cancel.';
        if (!confirm(msg)) {
            return;
        }
        // Don't allow Return button to be used again.
        saveStrategyActive = false

        // Mark that we returned this map.
        document.mappingform.savedMaps.value = false;

        document.mappingform.submit();
    }

}
