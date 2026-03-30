def re_arrange_usd_attributes_by_index(
    node, index_change=None, new_indexing=True, step_up=True, step_down=None
):
    """
    Rearrange the userdefined Attributes by index.
    By Default it moves the attribute up in the
    channelBox.
    Args:
            node(dagNode): The node the attributes belongs to.
            index_change(list): [oldIndex, newIndex].
            new_indexing(bool): New indexing of the attributes in the list.
            step_up(bool): newIndex = oldIndex + -1.
            step_down(bool): newIndex = oldIndex + 1.

    Return:
            list with dics: The rearranged attributes values as keys in a dic.
            Example:
                    [{'attrType': u'double',
                    'usd_attr': Attribute(u'null1.test_float'),
                    'index': 1, 'lock': False, 'defaultValue': 1.0,
                    'maxValue': 10.0, 'value': 0.0, 'minValue': 0.0,
                    'keyable': True, 'channelBox': False,
                    'output': [Attribute(u'null3.translateX')],
                    'input': [Attribute(u'null2.translateX')],
                    'hidden': False, 'enums': None}].
    """
    usd_attr = get_usd_attributes(node, index=True)
    op_value = 0
    if step_down:
        op_value = 1
        step_up = None
    if step_up:
        op_value = -1
        step_down = None
    if index_change:
        indexes = []
        for dic in usd_attr:
            indexes.append(dic["index"])
        if op_value:
            if index_change[0] + op_value >= 0:
                indexes.insert(
                    index_change[0] + op_value, indexes.pop(index_change[0])
                )
            else:
                _LOGGER.error("Negative newIndex not allowed")
                return
        else:
            indexes.insert(index_change[1], indexes.pop(index_change[0]))
        usd_attr = [usd_attr[x] for x in indexes]
    else:
        _LOGGER.error("You have to specifie the index_change")
    if new_indexing:
        for x in range(len(usd_attr)):
            usd_attr[x]["index"] = x
    return usd_attr


def re_arrange_usd_attributes_by_name(
    node, attribute_name=None, new_index=None, step_up=True, step_down=None
):
    """
    Rearrange a userdefined Attribute by name.
    By Default it moves the attribute up in the
    channelBox.
    Args:
            node(dagNode): The node the attributes belongs to.
            attribute_name(str): The name of the attribute.
            new_index(int): new position of the attribute.
            step_up(bool): new_index = oldIndex - 1.
            step_down(bool): new_index = oldIndex + 1.
    Return:
            list with dicts: The rearranged userdefined
            attributes.
    """
    usd_attr = get_usd_attributes(node=node, index=True)
    for x in range(len(usd_attr)):
        if usd_attr[x]["usd_attr"] == node.attr(attribute_name):
            old_index = usd_attr[x]["index"]
    if step_down:
        new_index = old_index + 1
        step_up = None
    if step_up:
        new_index = old_index - 1
        step_down = None
    index_change = [old_index, new_index]
    return re_arrange_usd_attributes_by_index(
        node=node,
        index_change=index_change,
        step_up=step_up,
        step_down=step_down,
    )


@DECORATORS.undo
def move_attribute_in_channel_box(
    node,
    attribute_name=None,
    exchange_attr_name=None,
    new_index=None,
    step_up=True,
    step_down=None,
):
    """
    Moves a selected user defined attribute in the channelBox
    by index or step by step.
    By Default it always takes the selected attribute in the
    channelBox and moves the attribute one step upwards.
    Args:
            node(dagNode): The node the attributes belongs to.
            attribute_name(str): The name of the attribute.
                                If None it takes the selected
                                attribute in the channelBox.
            exchange_attr_name(str): The name of the attribute
                                   to exchange with.
            new_index(int): new position of the attribute.
            step_up(bool): new_index = oldIndex - 1.
    """
    if not attribute_name:
        if len(pmc.channelBox("mainChannelBox", q=True, sma=True)) == 1:
            attribute_name = pmc.channelBox("mainChannelBox", q=True, sma=True)[
                0
            ]
        else:
            _LOGGER.error(
                "more then one selection in the channelBox not supported"
            )
            return
    if exchange_attr_name:
        step_up = None
        step_down = None
        usd_attr = get_usd_attributes(node=node, index=True)
        for attr_ in usd_attr:
            name = attr_["usd_attr"].split(".")[1]
            if name == exchange_attr_name:
                new_index = attr_["index"]
    usd_attr = re_arrange_usd_attributes_by_name(
        node=node,
        attribute_name=attribute_name,
        new_index=new_index,
        step_up=step_up,
        step_down=step_down,
    )

    def re_create_attr():
        """
        Executes the rebuild of the attributes.
        """
        if usd_attr:
            for x in usd_attr:
                x["usd_attr"].disconnect()
                x["usd_attr"].set(lock=False)
                x["usd_attr"].delete()
                # print(x["hidden"])
                # print(x["keyable"])
                # print(x["enums"])
                if x["attrType"] == "string":
                    node.addAttr(
                        x["usd_attr"].split(".")[1],
                        dt=x["attrType"],
                        hidden=x["hidden"],
                        keyable=x["keyable"],
                        en=x["enums"],
                    )
                    # node.attr(x["usd_attr"].split(".")[1]).set(x["value"], type=x["attrType"])
                else:
                    node.addAttr(
                        x["usd_attr"].split(".")[1],
                        at=x["attrType"],
                        hidden=x["hidden"],
                        keyable=x["keyable"],
                        en=x["enums"],
                    )
                    # node.attr(x["usd_attr"].split(".")[1]).set(
                    #     x["value"],
                    #     lock=x["lock"],
                    #     channelBox=x["channelBox"],
                    # )
                if x["input"]:
                    x["input"][0].connect(x["usd_attr"])
                if x["output"]:
                    for out in x["output"]:
                        x["usd_attr"].connect(out)
            _LOGGER.info("{} reordered in channelBox".format(attribute_name))

    re_create_attr()


@DECORATORS.undo
def transfer_attributes(
    source, target, output_connections=None, input_connections=None
):
    """
    Transfers the user defined attributes from a source object
    to a target object.
    By default, it's not recreating connections.
    Args:
            source(dagNode): The node with the source attributes.
            target(dagNode): The target node.
            output_connections(bool): Recreate output connections.
            input_connections(bool): Recreate input connections.
    Return:
            list with dicts: The user defined Attribute of the
            source object.
    """
    source_usd_attr = get_usd_attributes(node=source, index=True)
    if source_usd_attr:
        for attr_ in source_usd_attr:
            if attr_["attrType"] == "string":
                target.addAttr(
                    attr_["usd_attr"].split(".")[1],
                    dt=attr_["attrType"],
                    hidden=attr_["hidden"],
                    keyable=attr_["keyable"],
                    en=attr_["enums"],
                )
            else:
                target.addAttr(
                    attr_["usd_attr"].split(".")[1],
                    at=attr_["attrType"],
                    hidden=attr_["hidden"],
                    keyable=attr_["keyable"],
                    en=attr_["enums"],
                )
            target.attr(attr_["usd_attr"].split(".")[1]).set(
                attr_["value"],
                lock=attr_["lock"],
                keyable=attr_["keyable"],
                channelBox=attr_["channelBox"],
            )
            if input_connections:
                if attr_["input"]:
                    attr_["input"][0].connect(
                        pmc.PyNode(
                            str(attr_["usd_attr"]).replace(
                                str(source), str(target)
                            )
                        ),
                        force=True,
                    )
            if output_connections:
                if attr_["output"]:
                    for out in attr_["output"]:
                        pmc.PyNode(
                            str(attr_["usd_attr"]).replace(
                                str(source), str(target)
                            )
                        ).connect(out, force=True)
        _LOGGER.info(
            "Attributes transfered from {} to {}".format(
                str(source), str(target)
            )
        )
        return source_usd_attr
    _LOGGER.error("No user defined attributes found for {}".format(str(source)))

# Still under development
def rebuild_attributes_from_ud_data(usd_data_list, node=None):
    compound_childrens_atr_types = ["float", "double", "long", "short"]
    for data_dict in usd_data_list:
        if data_dict["attrType"] in compound_childrens_atr_types and data_dict["parent"] is not None:
            continue
        if not node:
            node = data_dict["ud_attr"].node()
        pmc.addAttr(node,
                    longName=data_dict["longName"],
                    shortName=data_dict["shortName"],
                    type=data_dict["attrType"],
                    keyable=data_dict["keyable"],
                    enumName=data_dict["enums"],
                    hidden=data_dict["hidden"],
                    maxValue=data_dict["maxValue"],
                    minValue=data_dict["minValue"])
        # try:
        #     pmc.addAttr(node, attr_name, e=True, dv=data_dict["defaultVaue"])
        # except:
        #     pass
        # node.attr(attr_name).set(data_dict["value"], channelBox=data_dict["channelBox"], lock=data_dict["lock"])