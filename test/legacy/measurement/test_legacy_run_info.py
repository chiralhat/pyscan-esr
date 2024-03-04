'''
Pytest functions to test the Runinfo class
'''

import pyscan as ps


#  ######## need to add tests for runinfo's different @property definitions.
def test_init_from_noparams():
    """
    Testing init from no paramaters in RunInfo

    Returns
    -------
    None

    """

    init_runinfo = ps.RunInfo()

    # for checking that loops have expected attributes
    def check_loops_have_attribute(loops, attribute_name):
        counter = 0
        for loop in loops:
            err_string = "runinfo loop" + str(counter) + " (Property Scan) " + attribute_name + " not intialized"
            assert hasattr(loop, attribute_name), err_string
            counter += 1

    # for checking that runinfo attributes are as expected
    def check_attribute(runinfo, attribute, attribute_name, expected):
        err_string1 = "runinfo " + attribute_name + " not initialized"
        assert hasattr(runinfo, attribute_name), err_string1
        err_string2 = "runinfo " + attribute_name + " not " + str(expected) + " when intialized"
        assert (attribute is expected or attribute == expected), err_string2

    # check that runinfo loops are initialized correctly
    def check_runinfo_loops():
        # check that loops 0 - 4 initialized
        for i in range(4):
            assert hasattr(init_runinfo, 'loop' + str(i)), "runinfo loop" + str(i) + " not initialized"

        # check that loops 0 - 4 initialized
        for loop in init_runinfo.loops:
            assert isinstance(loop, ps.PropertyScan), "runinfo loops not initialized as Property Scan"

        # check that loop attributes are initialized
        check_loops_have_attribute(init_runinfo.loops, 'scan_dict')
        check_loops_have_attribute(init_runinfo.loops, 'prop')
        check_loops_have_attribute(init_runinfo.loops, 'dt')
        check_loops_have_attribute(init_runinfo.loops, 'i')

        # check that each loops attributes are initialized correctly
        counter = 0
        for loop in init_runinfo.loops:
            # check that scan_dict initialized as empty {}
            err_string = "runinfo loop" + str(counter) + " (Property Scan) scan_dict not empty when intialized"
            assert loop.scan_dict == {}, err_string

            # check that prop initialized as None
            err_string = "runinfo loop" + str(counter) + " (Property Scan) prop not None when intialized"
            assert loop.prop is None, err_string

            # check that dt initialized as 0
            assert loop.dt == 0, "runinfo loop" + str(counter) + " (Property Scan) dt not 0 when intialized"

            # check that i initialized as 0
            assert loop.i == 0, "runinfo loop" + str(counter) + " (Property Scan) i not 0 when intialized"

            counter += 1

    check_runinfo_loops()

    # check that runinfo attributes are initialized correctly
    def check_runinfo_attributes():
        # check that static initialized correctly
        check_attribute(runinfo=init_runinfo, attribute=init_runinfo.static, attribute_name='static', expected={})

        # check that measured initialized correctly
        check_attribute(runinfo=init_runinfo, attribute=init_runinfo.measured, attribute_name='measured', expected=[])

        # check that measure_function initialized correctly
        check_attribute(runinfo=init_runinfo, attribute=init_runinfo.measure_function,
                        attribute_name='measure_function', expected=None)

        # check that trigger_function initialized correctly
        check_attribute(runinfo=init_runinfo, attribute=init_runinfo.trigger_function,
                        attribute_name='trigger_function', expected=None)

        # check that initial_pause initialized correctly
        check_attribute(runinfo=init_runinfo, attribute=init_runinfo.initial_pause,
                        attribute_name='initial_pause', expected=0.1)

        # check that average_d initialized correctly
        check_attribute(runinfo=init_runinfo, attribute=init_runinfo.average_d, attribute_name='average_d', expected=-1)

        # check that verbose initialized correctly
        check_attribute(runinfo=init_runinfo, attribute=init_runinfo.verbose, attribute_name='verbose', expected=False)

    check_runinfo_attributes()
