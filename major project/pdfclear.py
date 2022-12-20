import os
import snappy
from snappy import Product
from snappy import ProductIO
from snappy import ProductUtils
from snappy import WKTReader
from snappy import HashMap
from snappy import GPF
from snappy import jpy
# For shapefiles
import shapefile
import pygeoif
## Preprocessing functions
def applyOrbit(source):
    data = source
    params = HashMap()
    orbit =GPF.createProduct("Apply-Orbit-File", params, data)
    outfile = 'D:\\sar proj\\proj\\orbit'
    print('running orbit file')
    ProductIO.writeProduct(orbit, outfile, 'BEAM-DIMAP')
    #ProductIO.writeProduct(orbit, outfile, 'GeoTIFF')
    return orbit
def subset(product,x,y,width,height):
    parameters=snappy.HashMap()
    parameters.put('copyMetadata', True) 
    parameters.put('region', "%s,%s,%s,%s" %(x, y, width, height)) 
    subset =snappy.GPF.createProduct('Subset', parameters,product)
def calibration(product):
    parameters = HashMap()
    parameters.put('outputSigmaBand', True)
    parameters.put('sourceBands', 'Intensity_VV')
    parameters.put('selectedPolarisations', "VV")
    parameters.put('outputImageScaleInDb', False)
    print('cali done')
    return GPF.createProduct("Calibration", parameters, product)
def speckleFilter(product):
    parameters = HashMap()
    filterSizeY = '5'
    filterSizeX = '5'
    parameters.put('sourceBands', 'Sigma0_VV')
    parameters.put('filter', 'Lee')
    parameters.put('filterSizeX', filterSizeX)
    parameters.put('filterSizeY', filterSizeY)
    parameters.put('dampingFactor', '2')
    parameters.put('estimateENL', 'true')
    parameters.put('enl', '1.0')
    parameters.put('numLooksStr', '1')
    parameters.put('targetWindowSizeStr', '3x3')
    parameters.put('sigmaStr', '0.9')
    parameters.put('anSize', '50')
    print('filter done')
    sfilter=GPF.createProduct('Speckle-Filter', parameters, product)
    #ProductIO.writeProduct(sfilter, 'D:\\sar proj\\proj\\data\\filter', 'BEAM-DIMAP')
    return sfilter
def terrainCorrection(product):
    parameters = HashMap()
    parameters.put('demName', 'SRTM 3Sec')
    parameters.put('pixelSpacingInMeter', 10.0)
    parameters.put('sourceBands', 'Sigma0_VV')
    print('terrain done')
    return GPF.createProduct("Terrain-Correction", parameters, product)
# Flooding processing
def generateBinaryFlood(product):
    parameters = HashMap()
    BandDescriptor =snappy.jpy.get_type('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor')
    targetBand = BandDescriptor()
    targetBand.name = 'flooded'
    targetBand.type = 'uint8'
    targetBand.expression = '(Sigma0_VV < 1.13E-2) ? 1 : 0'
    targetBands =snappy.jpy.array('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor', 1)
    targetBands[0] = targetBand
    parameters.put('targetBands', targetBands)
    print('binary generated')
    return GPF.createProduct('BandMaths', parameters, product)
def maskKnownWater(product):
# Add land cover band
    parameters = HashMap()
    parameters.put("landCoverNames", "GlobCover")
    mask_with_land_cover = GPF.createProduct('AddLandCover', parameters,product)
    del parameters
    # Create binary water band
    BandDescriptor =snappy.jpy.get_type('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor')
    parameters = HashMap()
    targetBand = BandDescriptor()
    targetBand.name = 'BinaryWater'
    targetBand.type = 'uint8'
    targetBand.expression = '(land_cover_GlobCover == 210) ? 0 : 1'
    targetBands =snappy.jpy.array('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor', 1)
    targetBands[0] = targetBand
    parameters.put('targetBands', targetBands)
    water_mask = GPF.createProduct('BandMaths', parameters,mask_with_land_cover)
    del parameters
    parameters = HashMap()
    BandDescriptor =snappy.jpy.get_type('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor')
    try:
        water_mask.addBand(product.getBand("flooded"))
    except:
        pass
    targetBand = BandDescriptor()
    targetBand.name = 'Sigma0_VV_Flood_Masked'
    targetBand.type = 'uint8'
    targetBand.expression = '(BinaryWater == 1 && flooded == 1) ? 1 : 0'
    targetBands =snappy.jpy.array('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor', 1)
    targetBands[0] = targetBand
    parameters.put('targetBands', targetBands)
    print('masking done')
    return GPF.createProduct('BandMaths', parameters, water_mask)
print('started')
## GPF Initialization
GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()
path_to_sentinel_data ='D:\\sar proj\\final\\not flooded\\subset_6_of_subset_4_of_subset_1_of_subset_0_of_S1A_IW_GRDH_1SDV_20220503T003145_20220503T003210_043039_05239E_7F46.dim'
product = ProductIO.readProduct(path_to_sentinel_data)
print('product read')
product_subset=product
product_orbitfile = applyOrbit(product_subset)
product_preprocessed = terrainCorrection(speckleFilter(calibration(product_subset)))
print('pre-processing done')
bina=generateBinaryFlood(product_preprocessed)
ProductIO.writeProduct(bina, "D:\\sar proj\\final\\not flooded\\binary", 'BEAM-DIMAP')
print('binary mask done')
product_binaryflood = maskKnownWater(bina)
print('masked known water')
ProductIO.writeProduct(product_binaryflood, "D:\\sar proj\\final\\not flooded\\outp", 'BEAM-DIMAP')
print('finished')
