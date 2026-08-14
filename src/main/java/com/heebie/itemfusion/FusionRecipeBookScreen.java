package com.heebie.itemfusion;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.registries.ForgeRegistries;
import org.lwjgl.glfw.GLFW;

/**
 * Ingredient index: every item used in a fusion recipe, sorted by how often it
 * is used. Shows the item and its use count, never which recipes use it.
 *
 * T's UI rulings (2026-08-15): wider panel, page counter visible (centered,
 * not under the arrow button), items centered in their slots, closes on the
 * inventory key, search field that only types after you click it.
 */
public class FusionRecipeBookScreen extends Screen {
    private static final ResourceLocation BACKGROUND =
        new ResourceLocation(ItemFusion.MODID, "textures/gui/recipe_book.png");
    private static final int WIDTH = 216;
    private static final int HEIGHT = 196;
    private static final int COLS = 9;
    private static final int ROWS = 6;
    private static final int PER_PAGE = COLS * ROWS;
    private static final int GRID_X = 18;
    private static final int GRID_Y = 40;
    private static final int CELL = 20;

    private final Screen parent;
    private List<IngredientStats.Entry> all = List.of();
    private List<IngredientStats.Entry> filtered = List.of();
    private int page;
    private int left;
    private int top;
    private Button prev;
    private Button next;
    private EditBox search;

    public FusionRecipeBookScreen(Screen parent) {
        super(Component.translatable("gui.itemfusion.recipe_book"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        this.all = IngredientStats.get();
        this.left = (this.width - WIDTH) / 2;
        this.top = (this.height - HEIGHT) / 2;

        this.search = new EditBox(this.font, this.left + GRID_X, this.top + 20, COLS * CELL, 14,
            Component.translatable("gui.itemfusion.search"));
        this.search.setMaxLength(64);
        this.search.setHint(Component.translatable("gui.itemfusion.search")
            .withStyle(ChatFormatting.DARK_GRAY));
        this.search.setResponder(q -> {
            this.page = 0;
            refilter();
        });
        this.search.setFocused(false);
        this.addRenderableWidget(this.search);

        this.prev = Button.builder(Component.literal("<"), b -> turn(-1))
            .bounds(this.left + GRID_X, this.top + HEIGHT - 28, 20, 20).build();
        this.next = Button.builder(Component.literal(">"), b -> turn(1))
            .bounds(this.left + WIDTH - GRID_X - 20, this.top + HEIGHT - 28, 20, 20).build();
        this.addRenderableWidget(this.prev);
        this.addRenderableWidget(this.next);
        refilter();
    }

    private void refilter() {
        String q = this.search.getValue().trim().toLowerCase(Locale.ROOT);
        if (q.isEmpty()) {
            this.filtered = this.all;
        } else {
            List<IngredientStats.Entry> out = new ArrayList<>();
            for (IngredientStats.Entry e : this.all) {
                String display = e.stack().getHoverName().getString().toLowerCase(Locale.ROOT);
                ResourceLocation id = ForgeRegistries.ITEMS.getKey(e.stack().getItem());
                if (display.contains(q) || (id != null && id.toString().contains(q))) {
                    out.add(e);
                }
            }
            this.filtered = out;
        }
        if (this.page >= pageCount()) {
            this.page = pageCount() - 1;
        }
        updateButtons();
    }

    private int pageCount() {
        return Math.max(1, (this.filtered.size() + PER_PAGE - 1) / PER_PAGE);
    }

    private void turn(int delta) {
        this.page = Math.floorMod(this.page + delta, pageCount());
        updateButtons();
    }

    private void updateButtons() {
        boolean many = pageCount() > 1;
        this.prev.active = many;
        this.next.active = many;
    }

    @Override
    public void render(GuiGraphics g, int mouseX, int mouseY, float partialTick) {
        this.renderBackground(g);
        g.blit(BACKGROUND, this.left, this.top, 0, 0, WIDTH, HEIGHT);

        g.drawString(this.font, this.title, this.left + GRID_X, this.top + 8, 0x404040, false);

        super.render(g, mouseX, mouseY, partialTick);

        Component pages = Component.translatable("gui.itemfusion.page", this.page + 1, pageCount());
        g.drawString(this.font, pages,
            this.left + (WIDTH - this.font.width(pages)) / 2,
            this.top + HEIGHT - 22, 0x404040, false);

        int start = this.page * PER_PAGE;
        int end = Math.min(start + PER_PAGE, this.filtered.size());
        ItemStack hovered = ItemStack.EMPTY;
        int hoveredUses = 0;
        for (int i = start; i < end; ++i) {
            IngredientStats.Entry entry = this.filtered.get(i);
            int idx = i - start;
            int x = this.left + GRID_X + (idx % COLS) * CELL + 2;
            int y = this.top + GRID_Y + (idx / COLS) * CELL + 2;
            g.renderItem(entry.stack(), x, y);
            String uses = String.valueOf(entry.uses());
            g.pose().pushPose();
            g.pose().translate(0, 0, 200);
            g.drawString(this.font, uses, x + 17 - this.font.width(uses), y + 9, 0xFFFFFF, true);
            g.pose().popPose();
            if (mouseX >= x && mouseX < x + 16 && mouseY >= y && mouseY < y + 16) {
                hovered = entry.stack();
                hoveredUses = entry.uses();
            }
        }

        if (!hovered.isEmpty()) {
            var lines = new ArrayList<>(getTooltipFromItem(this.minecraft, hovered));
            lines.add(Component.translatable("gui.itemfusion.used_in", hoveredUses)
                .withStyle(ChatFormatting.GRAY));
            g.renderComponentTooltip(this.font, lines, mouseX, mouseY);
        }
    }

    @Override
    public boolean keyPressed(int keyCode, int scanCode, int modifiers) {
        if (this.search.isFocused()) {
            if (keyCode == GLFW.GLFW_KEY_ESCAPE || keyCode == GLFW.GLFW_KEY_ENTER) {
                this.search.setFocused(false);
                return true;
            }
            return this.search.keyPressed(keyCode, scanCode, modifiers) || true;
        }
        if (this.minecraft.options.keyInventory.matches(keyCode, scanCode)) {
            this.onClose();
            return true;
        }
        return super.keyPressed(keyCode, scanCode, modifiers);
    }

    @Override
    public boolean mouseClicked(double mouseX, double mouseY, int button) {
        boolean overSearch = mouseX >= this.search.getX() && mouseX < this.search.getX() + this.search.getWidth()
            && mouseY >= this.search.getY() && mouseY < this.search.getY() + this.search.getHeight();
        if (!overSearch && this.search.isFocused()) {
            this.search.setFocused(false);
        }
        return super.mouseClicked(mouseX, mouseY, button);
    }

    @Override
    public boolean mouseScrolled(double mouseX, double mouseY, double delta) {
        if (delta != 0 && pageCount() > 1) {
            turn(delta > 0 ? -1 : 1);
            return true;
        }
        return super.mouseScrolled(mouseX, mouseY, delta);
    }

    @Override
    public void onClose() {
        this.minecraft.setScreen(this.parent);
    }

    @Override
    public boolean isPauseScreen() {
        return false;
    }
}
