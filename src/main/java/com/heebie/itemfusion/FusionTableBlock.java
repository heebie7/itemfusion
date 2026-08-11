package com.heebie.itemfusion;

import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.ContainerLevelAccess;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;

public class FusionTableBlock extends Block {
    private static final Component CONTAINER_TITLE = Component.translatable("container.itemfusion.fusion_table");

    public FusionTableBlock(Properties properties) {
        super(properties);
    }

    @Override
    public InteractionResult use(BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hit) {
        if (level.isClientSide) {
            return InteractionResult.SUCCESS;
        }
        player.openMenu(new SimpleMenuProvider(
            (windowId, inv, p) -> new FusionTableMenu(windowId, inv, ContainerLevelAccess.create(level, pos)),
            CONTAINER_TITLE));
        return InteractionResult.CONSUME;
    }
}
